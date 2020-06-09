import os
import numpy as np
import matplotlib.pyplot as plt
import datetime
import PySimpleGUI as sg
import pathlib
from collections import Counter
from configparser import ConfigParser
from scipy.stats import norm


def locate_csv_file(window):
    file_path = read_config_info("csv_file_path")
    file_path = pathlib.Path(file_path)

    # First check if file exists. Keep asking until a file is provided
    while not file_path.is_file():
        answer = sg.PopupYesNo("Could not find csv file.\n"
                               "Do you want to locate it?\n"
                               "Clicking no will cause program to exit",
                               title="File not found")
        if answer == "Yes":
            file = sg.popup_get_file("Locate csv file", "CS Timer",
                                     file_types=(("csv", "*.csv"),))
            # clicking cancel returns None
            if file is not None:
                file_path = pathlib.Path(file)

        else:
            exit()

    # this open can fail if certain file types are selected
    # put this in a try block
    with open(file_path, "r") as f:
        text = f.readlines()

    # the first 10 characters of first line of correct file is "No.;Time;C"
    # use this to check if the file format is correct
    while text[0][:10] != "No.;Time;C" or not file_path.is_file():
        answer = sg.PopupYesNo("Unexpected file format.\n"
                               "Do you want to locate correct file?\n"
                               "Clicking no will cause program to exit",
                               title="Incorrect file format")
        if answer == "Yes":
            file = sg.popup_get_file("Locate csv file", "CS Timer",
                                     file_types=(("csv", "*.csv"),))
            # clicking cancel returns None
            if file is not None:
                file_path = pathlib.Path(file)
                if file_path.is_file():
                    with open(file_path, "r") as f:
                        text = f.readlines()
        else:
            exit()

    window.Element("CurrentFilePath").update(str(file_path))
    write_config_info("settings", "csv_file_path", str(file_path))

    return file_path


def check_if_integer(num):
    try:
        int(num)
        return True
    except ValueError:
        sg.popup_ok("Please enter an integer value")
        return False


def read_file(file_path):
    """

    :return:
    np_solve_times is a numpy array of the times in seconds
    solve_dates_list is a list of dates
    """
    solve_times_list = []
    solve_dates_list = []

    with open(file_path, "r") as f:
        text = f.readlines()

    # text[0] is "No.;Time;Comment;Scramble;Date;P.1"

    for line in text[1:]:  # start from second line, first line is header
        seconds = 0
        line = line.strip()  # remove new line tag \n
        line_items = line.split(";")
        # second and sixth column (element) are solve time but second column has DNF and +2 info
        # so use sixth column. So, DNF and +2 are not taken in to account at present
        solve_time = line_items[5]
        # fifth element is solve date and time (when the solve was done) separated by space
        solve_date = line_items[4]
        solve_date = solve_date.split(" ")[0]  # split to store date

        # Some of the times have the minute value, some don't
        # e.g. 1:25.68, 54.57 etc
        # split by the colon, then convert to seconds
        for i, t in enumerate(reversed(solve_time.split(":"))):
            seconds = seconds + float(t) * 60 ** i

        solve_times_list.append(seconds)
        solve_dates_list.append(solve_date)

    np_solve_times = np.array(solve_times_list)
    return np_solve_times, solve_dates_list


def calculate_averages(np_times, gui_window):
    best_time = np_times.min()
    total_solves = np_times.size
    last5 = np_times[-5:]  # reads last 5 times
    last12 = np_times[-12:]
    last100 = np_times[-100:]
    last500 = np_times[-500:]
    last1000 = np_times[-1000:]

    # remove best and worst times from best of 5 and best of 12
    last5 = np.delete(last5, [last5.argmin(), last5.argmax()])
    last12 = np.delete(last12, [last12.argmin(), last12.argmax()])

    last100 = np.sort(last100)  # AO100 is calculated by excluding the top/bottom 5 times
    last100 = last100[5:95]

    last500 = np.sort(last500)  # calculate AO500 in same manner as AO100 above
    last500 = last500[5:495]

    last1000 = np.sort(last1000)
    last1000 = last1000[10:990]  # take out first and last 10 times

    ao5 = round(last5.mean(), 2)
    ao12 = round(last12.mean(), 2)
    ao100 = round(last100.mean(), 2)
    ao500 = round(last500.mean(), 2)
    ao1000 = round(last1000.mean(), 2)
    # ao_all = round(np_times.mean(), 2)

    std5 = round(last5.std(ddof=1), 2)
    std12 = round(last12.std(ddof=1), 2)
    std100 = round(last100.std(ddof=1), 2)
    std500 = round(last500.std(ddof=1), 2)
    std1000 = round(last1000.std(ddof=1), 2)
    # std_all = round(np_times.std(), 2)

    gui_window.Element("PB").update(f"Best time = {best_time} : Total Solves = {total_solves}")
    gui_window.FindElement("AO5").update(f"Average of 5      : {ao5} (sigma: {std5})")
    gui_window.FindElement("AO12").update(f"Average of 12    : {ao12} (sigma: {std12})")
    gui_window.FindElement("AO100").update(f"Average of 100  : {ao100} (sigma: {std100})")
    gui_window.FindElement("AO500").update(f"Average of 500  : {ao500} (sigma: {std500})")
    gui_window.FindElement("AO1000").update(f"Average of 1000: {ao1000} (sigma: {std1000})")


def plot_graph(np_times):
    # A way to calculate moving average!
    # https://stackoverflow.com/questions/11352047
    cumulative_sum = np.cumsum(np.insert(np_times, 0, 0))  # Inserts a zero at the start
    width = 30  # Moving average interval size
    moving_average = (cumulative_sum[width:] - cumulative_sum[:-width]) / width
    x = np.arange(width - 1, np.size(np_times))  # plot moving averages starting at first value

    # print(f"Total time - {time.clock() - start_time}")

    # try these colors
    # 237 125 50 ed7d32 orange
    # 112 172 71 70ac47 green
    # 91 154 213 5b9ad5 blue
    # 253 191 0  fdbf00 yellow

    plt.figure(1)
    plt.plot(np_times[:], linewidth=1, color="#70ac47")
    plt.plot(x, moving_average, linewidth=2, color="#ed7d32")
    plt.grid(True)

    # step_size will be zero if num of solves is less than 39, so set to 1 in that case
    step_size = max(int(len(moving_average) / 10), 1)
    for i, value in enumerate(moving_average[::step_size]):
        plt.annotate(int(value), xy=(29 + i * step_size, value), color="black")

    plt.show(block=False)


def calculate_summary_stats_for_date(times, dates, tallied_dates):
    """
    This is used by calculate_solve_dates()
    :param times: np array of all the times
    :param dates: list of all dates including duplicates
    :param tallied_dates: list of tuples of date and tally
    :return:
    """
    message = ""
    for date, count in tallied_dates:
        # get indices of all dates that are equal to date
        indices = [i for i, item in enumerate(dates) if item == date]

        # times are stored in corresponding index, get summary from numpy array
        start, end = indices[0], indices[-1] + 1
        mean = round(times[start:end].mean(), 2)
        st_dev = round(times[start:end].std(ddof=1), 2)
        best = round(times[start:end].min(), 2)
        message = f"{message}" \
                  f"{date} : Solves {count}, mean {mean} ({st_dev}), best {best}\n"

    return message


def calculate_solve_dates(times, dates, gui_window):
    """
    :param dates: a list of dates including duplicates
    :param gui_window:
    :param times: numpy array of all the solve times
    :return:
    """

    c = Counter(dates)
    dates_tally = list(c.items())  # dates_tally is a tuple of (date, tally count)
    recent_dates = sorted(dates_tally[-10:], reverse=True)

    message = calculate_summary_stats_for_date(times, dates, recent_dates)
    gui_window.Element("Last10Days").update(message)

    most_solve_dates = sorted(dates_tally, key=lambda x: x[1], reverse=True)[:5]

    message = calculate_summary_stats_for_date(times, dates, most_solve_dates)
    gui_window.FindElement("MostSolves").update(message)


def last_n_days(times, dates, gui_window):
    """
    :param times: numpy array of all solve times
    :param dates: list of all solve dates including duplicates
    :param gui_window:
    :return:
    """
    c = Counter(dates)
    dates_tally = list(c.items())  # list of tuples of date and tally

    days = [3, 5, 7, 10, 15, 30]
    message = ""

    for n in days:
        recent_tally = sorted(dates_tally[-n:], reverse=True)
        total_count = 0
        compare_to_date = datetime.date.today() + datetime.timedelta(days=-n)
        for date, count in recent_tally:
            date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            if date > compare_to_date:
                total_count += count

        recent_times = times[-total_count:]
        mean = round(recent_times.mean(), 2)
        st_dev = round(recent_times.std(ddof=1), 2)
        best = recent_times.min()

        new_message = f"Last {n} days: Solves {total_count}, mean {mean} ({st_dev}), " \
                      f"best {best}\n"
        message = f"{message}{new_message}"

    gui_window.FindElement("RecentSolveCount").update(message)


def show_histogram(times):
    mu = times.mean()
    sigma = times.std(ddof=1)
    plt.hist(times, bins=30, density=True, rwidth=0.9)
    plt.plot(np.sort(times), norm.pdf(np.sort(times), mu, sigma))
    plt.show(block=False)


def read_config_info(option):
    config = ConfigParser()
    config_file = pathlib.Path(os.getcwd()).joinpath("cs_timer.ini")
    if not config_file.exists():
        config.add_section("settings")
        config.set("settings", "csv_file_path", "")
        config.set("settings", "n", "750")
        with open(config_file, "w") as f:
            config.write(f)

    config.read(config_file)
    return config.get("settings", option)


def write_config_info(section, option, value):
    config = ConfigParser()
    config_file = pathlib.Path(os.getcwd()).joinpath("cs_timer.ini")
    config.read(config_file)
    config.set(section, option, value)

    with open(config_file, "w") as f:
        config.write(f)


def gui_layout():
    button_width = 12
    n = read_config_info("n")

    options_frame = [
        [sg.Text("Currently loaded file"),
         sg.Button("Load New File", key="Refresh", size=(button_width, 1))],
        [sg.Text("File Path", size=(32, 2), key="CurrentFilePath")],
        [sg.Text("Show graph for last"),
         sg.Input(n, key="graph_n_points", size=(5, 1), enable_events=True),
         sg.Text("solves")],
        [sg.Button("Plot Graph", key="graph", size=(button_width, 1)),
         sg.Button("Plot Histogram", key="histogram", size=(button_width, 1))],
        [sg.Button("Exit", key="Exit", size=(button_width, 1))],
        # [sg.Button("Test", key="Test")]
    ]

    summary_statistics_frame_layout = [
        [sg.Text("", key="PB", size=(30, 1))],
        [sg.Text("AO5:    ", size=(30, 1), key="AO5")],
        [sg.Text("AO12:    ", size=(30, 1), key="AO12")],
        [sg.Text("AO100:    ", size=(30, 1), key="AO100")],
        [sg.Text("AO500:    ", size=(30, 1), key="AO500")],
        [sg.Text("AO1000:    ", size=(30, 1), key="AO1000")],
    ]

    recent_solves_frame = [
        [sg.Multiline("", size=(60, 7), disabled=True, key="RecentSolveCount",
                      font=("courier new", 11))]
    ]

    last_10_days_frame = [
        [sg.Multiline("", size=(60, 11), disabled=True, key="Last10Days",
                      font=("courier new", 11))]
    ]

    most_solves_frame = [
        [sg.Multiline("", size=(60, 7), disabled=True, key="MostSolves",
                      font=("courier new", 11))]
    ]

    layout = [
        [sg.Frame("Summary Statistics", summary_statistics_frame_layout),
         sg.VerticalSeparator(),
         sg.Frame("Options", options_frame)],
        [sg.Frame("Recent Solve Summary", recent_solves_frame)],
        [sg.Frame("Solve Summary for last 10 days", last_10_days_frame)],
        [sg.Frame("Most solves in a day", most_solves_frame)],
    ]

    return sg.Window("Solve Time Stats", layout=layout)


def event_loop():
    sg.theme("LightGreen")
    # are['Black', 'BlueMono', 'BluePurple', 'BrightColors', 'BrownBlue', 'Dark'
    window = gui_layout()
    window.read(10)
    csv_file = locate_csv_file(window)
    solve_times, solve_dates = read_file(csv_file)
    calculate_averages(solve_times, window)
    calculate_solve_dates(solve_times, solve_dates, window)
    last_n_days(solve_times, solve_dates, window)

    while True:
        event, values = window.read()

        if event in (None, "Exit"):
            break

        if event == "Refresh":
            write_config_info("settings", "csv_file_path", "")
            csv_file = locate_csv_file(window)
            solve_times, solve_dates = read_file(csv_file)
            calculate_averages(solve_times, window)
            calculate_solve_dates(solve_times, solve_dates, window)
            last_n_days(solve_times, solve_dates, window)

        if event == "graph":
            n = values["graph_n_points"]
            if check_if_integer(n):
                n = int(values["graph_n_points"])
                write_config_info("settings", "n", str(n))
                plot_graph(solve_times[-n:])

        if event == "histogram":
            n = values["graph_n_points"]
            if check_if_integer(n):
                n = int(values["graph_n_points"])
                write_config_info("settings", "n", str(n))
                show_histogram(solve_times[-n:])


def main():
    event_loop()


if __name__ == "__main__":
    main()

# todo
# check if n (graph for last solve) is numeric

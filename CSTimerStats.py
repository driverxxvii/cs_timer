import os
import pathlib
import datetime
import pandas as pd
import PySimpleGUI as sg
import matplotlib.pyplot as plt
from scipy.stats import norm
from configparser import ConfigParser


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


def time_to_seconds(solve_time):
    """
    converts a string of the form mm:ss.xx or ss.xx to seconds only
    :param solve_time: a string of the form mm:ss.xx or ss.xx
    :return: float seconds
    """
    seconds = 0
    for i, t in enumerate(reversed(solve_time.split(":"))):
        seconds = seconds + float(t) * 60 ** i

    return seconds


def read_file(file_path):

    df = pd.read_csv(file_path, )
    df.columns = ["Header"]      # rename header

    # Split columns by ';' delimiter.
    df[
        ["solve_num",
         "solve_time_with_info",
         "comment",
         "scramble",
         "date",
         "solve_time"]] = df["Header"].str.split(";", expand=True)

    # drop unused columns
    df.drop(["Header", "solve_time_with_info", "comment"], axis=1, inplace=True)

    # Convert solve time from mm:ss.xx to ss.xx
    df["solve_time"] = df["solve_time"].apply(time_to_seconds)

    # Convert date to datetime objects
    df["date"] = pd.to_datetime(df["date"], )
    df["date_only"] = df["date"].dt.date
    df["date_only"] = pd.to_datetime((df["date_only"]))

    # return df

    # return np_solve_times, solve_dates_list, df
    return df


def calculate_averages(df, gui_window):
    solve_times = df["solve_time"]
    # remove best and worst times from best of 5 and best of 12
    # AO100 and AO500 is calculated by excluding the top/bottom 5 times
    # AO1000 is calculated by excluding the top/bottom 10 times

    # Get relevant tail, then sort values and finally slice for required values.
    solve_times_5 = solve_times.tail(5).sort_values().iloc[1:4]
    solve_times_12 = solve_times.tail(12).sort_values().iloc[1:11]
    solve_times_100 = solve_times.tail(100).sort_values().iloc[5:95]
    solve_times_500 = solve_times.tail(500).sort_values().iloc[5:495]
    solve_times_1000 = solve_times.tail(1000).sort_values().iloc[10:990]

    best_time = solve_times.min()
    total_solves = len(solve_times)

    ao5, ao12, ao100, ao500, ao1000 = [round(solve_times_5.mean(), 2),
                                       round(solve_times_12.mean(), 2),
                                       round(solve_times_100.mean(), 2),
                                       round(solve_times_500.mean(), 2),
                                       round(solve_times_1000.mean(), 2)]

    std5, std12, std100, std500, std1000 = [round(solve_times_5.std(), 2),
                                            round(solve_times_12.std(), 2),
                                            round(solve_times_100.std(), 2),
                                            round(solve_times_500.std(), 2),
                                            round(solve_times_1000.std(), 2),
                                            ]

    gui_window.Element("PB").update(f"Best time = {best_time} : Total Solves = {total_solves}")
    gui_window.FindElement("AO5").update(f"Average of 5      : {ao5} (sigma: {std5})")
    gui_window.FindElement("AO12").update(f"Average of 12    : {ao12} (sigma: {std12})")
    gui_window.FindElement("AO100").update(f"Average of 100  : {ao100} (sigma: {std100})")
    gui_window.FindElement("AO500").update(f"Average of 500  : {ao500} (sigma: {std500})")
    gui_window.FindElement("AO1000").update(f"Average of 1000: {ao1000} (sigma: {std1000})")


def plot_graph(df, n):
    if n > len(df):
        n = len(df)

    solve_times = df["solve_time"].tail(n)
    width = 30  # Moving average interval size

    plt.figure(1)
    rolling_mean = solve_times.rolling(window=width).mean()
    plt.plot(solve_times, linewidth=1, color="#70ac47")
    plt.plot(rolling_mean, linewidth=2, color="#ed7d32")

    plt.grid(True)

    # only show moving average if n > width
    if n > width:
        indices = solve_times.index.values.tolist()
        moving_average = rolling_mean.values.tolist()
        # step_size will be zero if num of solves is less than 39, so set to 1 in that case
        step_size = max(int((len(indices) - width+1) / 10), 1)
        for i, value in enumerate(moving_average[width::step_size]):
            plt.annotate(int(value), xy=(indices[width + i * step_size], value))

        plt.annotate(int(moving_average[-1]), xy=(indices[-1], moving_average[-1]))

    plt.show(block=False)


def last_10_days(df, gui_window):
    date_group = df.groupby(["date_only"])
    dg_agg = date_group["solve_time"].agg(["count", "mean", "std", "min", "max"]).round(2)
    dg_agg.sort_index(inplace=True, ascending=False)
    dg_agg.reset_index(inplace=True)

    dg_agg.rename({"date_only": "Date",
                   "count": "Solves",
                   "mean": "Mean",
                   "std": "st. dev",
                   "min": "Best",
                   "max": "Worst"},
                  axis=1, inplace=True)

    dg_agg = dg_agg.head(10)
    message = dg_agg.to_string(header=True, index=False)
    gui_window.Element("Last10Days").update(message)


def top5days(df, gui_window):
    date_group = df.groupby(["date_only"])
    dg_agg = date_group["solve_time"].agg(["count", "mean", "std", "min", "max"]).round(2)
    dg_agg_sorted = dg_agg.sort_values("count", ascending=False).head(5)
    dg_agg_sorted.reset_index(inplace=True)

    # df.rename({"Header": "Index"}, axis=1, inplace=True)
    dg_agg_sorted.rename({"date_only": "Date",
                          "count": "Solves",
                          "mean": "Mean",
                          "std": "st. dev",
                          "min": "Best",
                          "max": "Worst"},
                         axis=1, inplace=True)
    message = dg_agg_sorted.to_string(header=True, index=False)
    gui_window.FindElement("MostSolves").update(message)


def last_n_days(df, gui_window):
    message = ""
    days = [3, 5, 7, 10, 15, 30]

    data = {}
    last, solves, means, st_devs, bests, worsts = [], [], [], [], [], []

    for n in days:
        n_days_filter = df["date_only"] >= datetime.datetime.today() + datetime.timedelta(days=-n)
        new_df = df.loc[n_days_filter, "solve_time"]
        mean = round(new_df.mean(), 2)
        st_dev = round(new_df.std(ddof=1), 2)
        best = new_df.min()
        # worst = new_df.nlargest(3).to_string(index=False, header=False)
        # worst = worst.replace("\n", "")
        worst = new_df.max()
        total_count = len(new_df)

        last.append(f"{n} days")
        solves.append(total_count)
        means.append(mean)
        st_devs.append(st_dev)
        bests.append(best)
        worsts.append(worst)

    data["Last"] = last
    data["Solves"] = solves
    data["Mean"] = means
    data["st. dev"] = st_devs
    data["Best"] = bests
    data["Worst"] = worsts

    summary_df = pd.DataFrame.from_dict(data)
    message = summary_df.to_string(header=True, index=False)
    gui_window.FindElement("RecentSolveCount").update(message)


def show_histogram(df, n):
    solve_times = df["solve_time"].tail(n)
    mu = solve_times.mean()
    sigma = solve_times.std()
    solve_times.sort_values(inplace=True)
    plt.hist(solve_times, bins=30, density=True, rwidth=0.9)
    plt.plot(solve_times, norm.pdf(solve_times, mu, sigma), color="#ed7d32")
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
    df = read_file(csv_file)
    calculate_averages(df, window)
    last_n_days(df, window)
    last_10_days(df, window)
    top5days(df, window)

    plt.tight_layout()
    plt.style.use("seaborn")

    while True:
        event, values = window.read()

        if event in (None, "Exit"):
            break

        if event == "Refresh":
            write_config_info("settings", "csv_file_path", "")
            csv_file = locate_csv_file(window)
            solve_times, solve_dates, df = read_file(csv_file)
            calculate_averages(df, window)
            last_n_days(df, window)
            last_10_days(df, window)
            top5days(df, window)

        if event == "graph":
            n = values["graph_n_points"]
            if check_if_integer(n):
                n = int(values["graph_n_points"])
                write_config_info("settings", "n", str(n))
                plot_graph(df, n)

        if event == "histogram":
            n = values["graph_n_points"]
            if check_if_integer(n):
                n = int(values["graph_n_points"])
                write_config_info("settings", "n", str(n))
                show_histogram(df, n)


def main():
    event_loop()


if __name__ == "__main__":
    main()

# todo

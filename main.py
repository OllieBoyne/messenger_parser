## looks through all json messages in a folder, does some operations on them

import os
import json
import pandas as pd
import emoji
from tqdm import tqdm
import argparse
from matplotlib import pyplot as plt
import matplotlib
from matplotlib.patches import FancyArrowPatch
import numpy as np
from tabulate import tabulate
from collections import defaultdict
from copy import deepcopy
import time
matplotlib.use('TkAgg')

parser = argparse.ArgumentParser()

parser.add_argument('--directory', type=str, help='Directory of files to look at', required=True)
parser.add_argument('--output_dir', type=str, default='', help='Directory to output logs to')

parser.add_argument('--past_n_days', type=int, default=-1, help="Only look at messages from the past n days")
parser.add_argument('--show_graph', action='store_true', help="Show plot of graph of messages over time")
parser.add_argument('--graph_freq', type=str, choices=['day', 'week', 'month'], default='week',
                    help="Frequency of data for graph")

parser.add_argument('--show_react_network', action='store_true', help="Show plot of reactions between people")


reacts = {
    "laugh": "😆",
    "heart_eyes": "😍",
    "heart_react": "❤",
    "thumbs_up": "👍",
    "thumbs_down": "👎",
}

_emoji_decoder = {} # speed up emoji decoding by storing common decodes


class MessengerData:
    def __init__(self):
        self.message_log = {}
        self.react_log = {}
        self.mention_count = {}
        self.streak_log = {}  # person : list of timestamps for longest streak

        # for measuring longest streak
        self.cur_holder = None
        self.cur_streak = 0
        self.streak_timestamps = []

    def store_message(self, msg):
        """Store message in message log, and update streak counter"""
        sender = msg['sender_name']
        self.message_log[msg['timestamp_ms']] = [msg.get('content', ''), sender]

        # Increment longest streak of messages
        if self.cur_holder == sender:
            self.streak_timestamps.append(msg['timestamp_ms'])
        else:
            if len(self.streak_log.get(self.cur_holder, [])) < len(self.streak_timestamps):
                self.streak_log[self.cur_holder] = self.streak_timestamps

            self.cur_holder = sender  # move to new holder
            self.streak_timestamps = [msg['timestamp_ms']]

    def store_react(self, msg, react):
        """Store react in react log"""
        self.react_log[msg['timestamp_ms']] = [react['reaction'], react['actor'], msg['sender_name']]

    def parse_log(self, log_name, columns):
        """log_name = message or react"""
        log = getattr(self, f"{log_name}_log")
        df = pd.DataFrame.from_dict(log, orient='index', columns=columns)
        df.index = pd.to_datetime(df.index, unit='ms')
        df.index.name = 'timestamp'
        setattr(self, f"{log_name}_log", df)

    def post(self):
        self.parse_log('message', ['content', 'sender'])
        self.parse_log('react', ['emoji', 'sender', 'receiver'])

        # parse streaks log
        df = pd.DataFrame.from_dict({k: [v] for k, v in self.streak_log.items()}, orient='index',
                                    columns=['timestamps'])
        df['streak'] = list(map(len, df['timestamps']))
        df['start'] = [i[-1] for i in df['timestamps']]  # NOTE: timestamps stored in reverse order
        df['end'] = [i[0] for i in df['timestamps']]
        df['start'] = pd.to_datetime(df['start'], unit='ms')
        df['end'] = pd.to_datetime(df['end'], unit='ms')
        df.index.name = 'Name'
        self.streak_log = df

    def save_all(self, output_dir):
        """Save all logs to output dir"""
        for log_type in ['message', 'react', 'streak']:
            getattr(self, f'{log_type}_log').to_csv(os.path.join(output_dir, f'{log_type}s.csv'))


def _parse_emoji(react_bytes):
    """Given in the format \\uxxxx\\uxxx..., convert to a singlr U+1... format"""
    if react_bytes in _emoji_decoder:
        return _emoji_decoder[react_bytes]
    else:
        rb = react_bytes.encode().decode('unicode_escape')
        s = emoji.emojize(rb).encode('latin1').decode('utf8')
        _emoji_decoder[react_bytes] = s # store for fast retrieval
        return s


def _preparse(file):
    out = ""
    with tqdm(file.readlines()) as tqdm_iterator:
        tqdm_iterator.set_description("Parsing file...")
        for line in tqdm_iterator:
            if '\"reaction\":' in line:
                react_bytes = line.split('\"')[3]
                line = line.replace(react_bytes, _parse_emoji(react_bytes))
            out += line

    return out


def get_data(files: list, past_n_days = -1) -> MessengerData:
    """Given list of json files, return dict of person : num messages sent"""

    messenger_data = MessengerData()

    for file in files:
        with open(file) as infile:
            json_text = _preparse(infile)
            data = json.loads(json_text)
            for msg in data['messages']:
                if past_n_days > 0 and msg['timestamp_ms'] < (time.time() - past_n_days * 24 * 60 * 60) * 1000:
                    continue

                # store message
                messenger_data.store_message(msg)

                # add reactions to table
                for react in msg.get('reactions', []):
                    messenger_data.store_react(msg, react)

    messenger_data.post()  # post process
    return messenger_data


def line_break(report):
    report.append("\n------\n")


def print_report(messenger_data: MessengerData, loc=None):
    """Print messenger data, both to console, and file if provided"""

    report = ["------"]

    # Messages per person
    report.append("Messages per person")
    msgs_per_person = messenger_data.message_log.groupby(['sender']).size().sort_values(ascending=False)
    tot_messages = msgs_per_person.sum()
    report.append(tabulate(
        [[name, msgs_per_person[name], f'{100 * msgs_per_person[name] / tot_messages:.1f}%'] for name in
         msgs_per_person.index],
        headers=['Name', 'Messages', '% of total'], tablefmt="github"))

    log_per_person = pd.DataFrame(dict(name=msgs_per_person.index, msgs_sent=msgs_per_person.values)) # create df here to start logging things together
    log_per_person = log_per_person.set_index('name')

    # Reacts per person
    line_break(report)
    report.append("Reacts per person")
    reacts_by_sender = messenger_data.react_log.groupby('sender').size()  # by sender
    reacts_by_receiver = messenger_data.react_log.groupby('receiver').size().sort_values(ascending=False)  # by receiver
    report.append(
        tabulate([[name, reacts_by_sender[name], reacts_by_receiver[name]] for name in reacts_by_receiver.index],
                 headers=['Name', 'Sent', 'Received'], tablefmt="github"))

    # Reacts per type
    line_break(report)
    react_headers = '😆😍❤👍👎'
    report.append('Type of reacts given')
    reacts_by_sender_type = messenger_data.react_log.groupby(['sender', 'emoji']).size()
    report.append(
        tabulate([[name, *[reacts_by_sender_type.get((name, e), 0) for e in react_headers]] for name in reacts_by_sender.index],
                 headers=['Name', *react_headers], tablefmt="github")
    )

    line_break(report)
    report.append('Type of reacts received')
    reacts_by_receiver_type = messenger_data.react_log.groupby(['receiver', 'emoji']).size()
    report.append(
        tabulate([[name, *[reacts_by_receiver_type.get((name, e), 0) for e in react_headers]] for name in reacts_by_receiver.index],
                 headers=['Name', *react_headers], tablefmt="github")
    )


    # Streaks per person
    line_break(report)
    report.append("Streaks of longest messages")
    sl = messenger_data.streak_log
    report.append(tabulate(
        [[name, sl.loc[name]['streak'], sl.loc[name]['start'], sl.loc[name]['end']] for name in
         sl['streak'].sort_values(ascending=False).index],
        headers=['Name', 'Streak', 'Start' 'End'], tablefmt='github'))

    # Engagement - ratio of reacts received per message sent
    # Set default reacts_by_receiver to 0
    for name in messenger_data.message_log['sender'].unique():
        if name not in reacts_by_receiver:
            reacts_by_receiver[name] = 0

    line_break(report)
    report.append("Engagement - how many reacts per post")
    log_per_person['reacts_received'] = reacts_by_receiver[log_per_person.index]
    log_per_person['engagement'] = log_per_person.reacts_received / log_per_person.msgs_sent
    log_per_person = log_per_person.sort_values(by='engagement', ascending=False)
    report.append(tabulate([[name, log_per_person.engagement[name]] for name in log_per_person.index],
                  headers=['Name', 'Reacts received per message sent'], tablefmt='github'))

    print(*report, sep="\n")

    if loc is not None:
        with open(loc, 'w') as outfile:
            print(*report, sep="\n", file=outfile)


def plot_chat_volume(messenger_data, plot_by='week'):
    """Plot the frequency of messages over time.
    plot_by must be week, day, or month.
    Produces a stacked figure"""
    msg_log = messenger_data.message_log
    width = {'day': 1, 'week': 7, 'month': 30}

    fig, ax = plt.subplots(nrows=2)

    # if plot_by == 'day':
    #     count = msg_log.groupby([msg_log.index.date]).size()
    #     x = count.index
    if plot_by in ['day', 'week', 'month']:
        count = msg_log.groupby([msg_log.to_period(freq=plot_by[0]).index]).size()
        x = count.index.start_time  # x value is start date of week
    else:
        raise NotImplementedError(f"plot_by must be one of week, day, month - not '{plot_by}'")

    ax[0].bar(x, count.values, width=width[plot_by])
    ax[0].set_xlabel('Date')
    ax[0].set_ylabel(f'Messages per {plot_by}')

    for user in messenger_data.message_log['sender'].unique():
        msg_log_person = msg_log[msg_log['sender'] == user]
        if plot_by in ['day', 'week', 'month']:
            count = msg_log_person.groupby([msg_log_person.to_period(freq=plot_by[0]).index]).size()
            x = count.index.start_time  # x value is start date of week
        else:
            raise NotImplementedError(f"plot_by must be one of week, day, month - not '{plot_by}'")

        ax[1].plot(x, count, label=user)
    ax[1].legend()
    ax[1].set_xlabel('Date')
    ax[1].set_xlabel(f'Messagers per {plot_by}')


def plot_react_network(messenger_data: MessengerData):
    """Plot graph showing connectivity based on number of reacts"""
    users = messenger_data.message_log['sender'].unique()
    reacts_by_sender = messenger_data.react_log.groupby(['sender','receiver']).size()

    vmax = max(reacts_by_sender)
    fig, ax = plt.subplots()
    ax.axis('off')
    theta = np.linspace(0, 2*np.pi, len(users)+1)
    C = lambda i, R=1: np.array((R * np.cos(theta[i]), R*np.sin(theta[i])))

    seed = np.random.seed(5)
    cols = np.random.rand(len(users), 3)

    data = defaultdict(dict)

    for i, name in enumerate(users):
        circle = plt.Circle(C(i), 0.06, zorder=0, facecolor=cols[i])
        plt.text(*C(i,R=1.2), s=name.replace(" ", "\n"), ha='center')

        style = 'Simple, tail_width=1, head_width=10, head_length=10'
        kw=dict(arrowstyle=style)

        for j, other in [(j,u) for j,u in enumerate(users) if u is not name]:
            val = reacts_by_sender.get((name, other), 0)
            patch = FancyArrowPatch(C(i), (C(j)), alpha=val/vmax,
                        color=cols[i], connectionstyle="arc3,rad=0.1", **kw)
            # length_includes_head=True,
            ax.add_patch(patch)
            data[name][other] = val


        ax.add_patch(circle)
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)

    #     Print as a table
    first_name_only = lambda s: s.split()[0]
    print(tabulate([['From ' + first_name_only(name), *[data[name].get(u,'-') for u in users]] for name in users],
                   headers=['To ' + first_name_only(s) for s in users], tablefmt='github'))


if __name__ == "__main__":

    args = parser.parse_args()

    # list of all valid message files
    files = [os.path.join(args.directory, f) for f in os.listdir(args.directory) if f.endswith('.json')]
    sorted(files)  # make sure in alphabetical (reverse chronological) order
    messenger_data = get_data(files, past_n_days=args.past_n_days)

    output_dir = args.output_dir
    if output_dir != '':
        os.makedirs(output_dir, exist_ok=True)
        messenger_data.save_all(output_dir)

    print_report(messenger_data, loc=os.path.join(output_dir, 'log.txt') if output_dir != "" else None)

    if args.show_graph:
        plot_chat_volume(messenger_data, plot_by=args.graph_freq)

    if args.show_react_network:
        plot_react_network(messenger_data)

    plt.show()
## looks through all json messages in a folder, does some operations on them

import os
import json
import pandas as pd
import emoji
from tqdm import tqdm

from matplotlib import pyplot as plt
import matplotlib

matplotlib.use('TkAgg')

reacts = {
    "laugh": "😆",
    "heart_eyes": "😍",
    "heart_react": "❤",
    "thumbs_up": "👍",
    "thumbs_down": "👎",
}


def _parse_unicode(react_bytes):
    """Given in the format \\uxxxx\\uxxx..., convert to a singlr U+1... format"""
    react_bytes = react_bytes.encode().decode('unicode_escape')
    s = emoji.emojize(react_bytes).encode('latin1').decode('utf8')
    return s


def _preparse(file):
    out = ""
    with tqdm(file.readlines()) as tqdm_iterator:
        tqdm_iterator.set_description("Parsing file...")
        for line in tqdm_iterator:
            if '\"reaction\":' in line:
                react_bytes = line.split('\"')[3]
                line = line.replace(react_bytes, _parse_unicode(react_bytes))
            out += line
    return out


def messages_by_person(files):
    """Given list of json files, return dict of person : num messages sent"""

    out = {
        'message_log': {},
        'react_log': {},
        'mention_count': {},
        'streak_count': {},
        'streak_text': {},
    }

    # for measuring longest streak
    cur_holder = None
    cur_streak = 0
    streak_msgs = []

    for file in files:
        with open(file) as infile:
            json_text = _preparse(infile)
            data = json.loads(json_text)

        with tqdm(data['messages']) as tqdm_iterator:
            tqdm_iterator.set_description("Reading messages: ")
            for msg in tqdm_iterator:
                sender = msg['sender_name']
                timestamp = msg['timestamp_ms']

                # store message
                out['message_log'][timestamp] = [msg.get('content', ''), sender]

                # add reactions to table
                if 'reactions' in msg:
                    for react in msg['reactions']:
                        out['react_log'][timestamp] = [react['reaction'], react['actor'], msg['sender_name']]

                # count number of mentions
                if 'content' in msg:
                    if '@' in msg['content']:
                        tag = [i for i in msg['content'].split(" ") if i.startswith('@')]
                        for t in tag:
                            out['mention_count'][t] = out.get(t, 0) + 1

                # for measuring longest streak
                if cur_holder == sender:
                    cur_streak += 1
                    streak_msgs.append(msg.get('content', ''))
                else:
                    if out['streak_count'].get(cur_holder, 0) < cur_streak:
                        out['streak_text'][cur_holder] = streak_msgs
                    out[cur_holder] = max(out['streak_count'].get(cur_holder, 0),
                                          cur_streak)  # register prev holder's record
                    cur_holder = sender  # move to new holder
                    cur_streak = 1
                    streak_msgs = []

    # convert to pandas dataframes
    out['message_log'] = pd.DataFrame.from_dict(out['message_log'], orient='index', columns=['content', 'sender'])
    out['message_log'].index = pd.to_datetime(out['message_log'].index, unit='ms')
    out['message_log'].index.name = 'timestamp'

    out['react_log'] = pd.DataFrame.from_dict(out['react_log'], orient='index', columns=['emoji', 'sender', 'receiver'])
    out['react_log'].index = pd.to_datetime(out['react_log'].index, unit='ms')
    out['react_log'].index.name = 'timestamp'

    return out


def plot_chat_volume(msg_log, plot_by='week'):
    """Plot the frequency of messages over time.
    plot_by must be week or day"""

    if plot_by == 'day':
        count = msg_log.groupby([msg_log.index.date]).size()
        x = count.index
    elif plot_by in ['week', 'month']:
        count = msg_log.groupby([msg_log.to_period(freq=plot_by[0]).index]).size()
        x = count.index.start_time  # x value is start date of week
    else:
        raise NotImplementedError(f"plot_by must be one of week, day, month - not '{plot_by}'")

    width = {'day':1, 'week':7, 'month': 30}
    plt.bar(x, count.values, width=width[plot_by])
    plt.xlabel('Date')
    plt.ylabel(f'Messages per {plot_by}')
    plt.show()


if __name__ == "__main__":
    files = [os.path.join(src, f) for f in os.listdir(src) if f.endswith('.json')][-1:]
    res = messages_by_person(files)

    # for key in ['message_count', 'char_count', 'mention_count']:
    #     print("------")
    #     print(key.upper())
    #
    #     data = res[key]
    #
    #     for name in sorted(data.keys(), key=lambda x: data[x], reverse=True):
    #         print(name, data[name], f"{100* data[name] / sum(data.values()):.1f}%")
    #
    # # print react report
    # print("------")
    # print("REACTS")
    # react_log = res['react_log']
    #
    # print("\nRANKED BY SENDER:")
    # by_sender = react_log['from'].value_counts()
    # print(by_sender)
    #
    # print("\nRANKED BY RECEIVER")
    # by_receiver = react_log['to'].value_counts()
    # print(by_receiver)
    #
    # print("\nRANKED BY RECEIVER, BY TYPE:")
    # by_receiver_by_type = react_log.groupby(['to', 'react']).size()
    #
    # print(by_receiver_by_type.head(100))
    #
    # for name, emoji in reacts.items():
    #     emoji_data = react_log.loc[react_log['react'] == emoji]
    #     tab = emoji_data.groupby(['to']).size().sort_values(ascending=False)
    #     print("------")
    #     print(f"{name}, {emoji}")
    #     print(tab)

    plot_chat_volume(res['message_log'], plot_by='week')

    # print streaks separately
    # print(name, d[name], s[name])

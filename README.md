# Facebook messenger parser

This script provides analysis on downloaded data from Facebook.

Once you request your chat history from Facebook, you can use this script to analyse a chat log, viewing who sends the most messages in a group chat, when messages have been sent over time, who has received/given the most reactions, and more!

## Getting the data

- On Facebook, go to Settings > Your Facebook Information > Download your Information
- Select Date range: All of my data, Format: JSON, Media quality: low (for faster download)
- Untick all options under `Your information` below except for Messages
- Click `Create File`
- Wait (approx. 12 hours) for Facebook to provide download link
- Download and unzip

## Running the script

Run main.py, with the following options:

- `--directory`: path to directory of conversation you would like to analyse
    * For example,`facebook-<username>/messages/inbox/example_aaaaaaa`
- `--export_dir`: [optional] path to directory to export .csv files of message, react and streak csv files. Also outputs log of results as text file here, which is also printed to console. Not output if left blank.
- `--show_graph`: plot graph of messages over time
- `--graph_freq`: sample width for graph (day, week or month) - default week

Example usage:

`python main.py --directory <directory> --export_dir outputs --show_graph --graph_freq month`
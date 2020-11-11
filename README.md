# Facebook messenger parser

This script provides analysis on downloaded data from Facebook

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
- `--outfile`: [optional] path to file to write output report to. Always printed to console
- `--show_graph`: plot graph of messages over time
- `--graph_freq`: sample width for graph (day, week or month) - default week

example usage:

`python main.py --directory <directory> --outfile out.txt --show_graph --graph_freq month`
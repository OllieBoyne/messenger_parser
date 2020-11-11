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
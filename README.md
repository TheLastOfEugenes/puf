# Presentation
Ports and Urls Filter is a tool supposed to help you fuzz targets. Its main functionalities are
- Presentation of the results
- Quick start of fuzz and nmap commands
- Handling of results through files and folders
- Storage of all results and easy filtering
- Management of targets
- Being customisable

The tool itself is started locally using a flask server and is accessible in a web browser, allowing easier handling with less problems.

# Installation

For classic installation, here is the command to clone the repo:
```
git clone https://github.com/TheLastOfEugenes/puf.git
```

For exegol users: here is a quick 2-liner to install puf and include it to your image.
```
echo "wget -qO- https://github.com/TheLastOfEugenes/puf/archive/refs/tags/v1.0.tar.gz | tar -xz -C /opt/ && mv /opt/puf-1.0 /opt/puf" > $HOME/.exegol/my-resources/setup/load_user_setup.sh
echo "alias puf='python3 /opt/puf/app.py'" > $HOME/.exegol/my-resources/setup/zsh/aliases
```

# Use guide

## Presentation of the results

Instead of having multiple shells open and having to cat/jq every result as soon as you wonder what interesting port was exposed you can simply keep this server open in your web browser while you go about your tests and focus on something else and get it back whenever you want, really fast.

## Quick commands

The commands have been based on a previous bash command used to start different scans and sort them in a file system easily readable. These commands are the following:
```
# nmap scan
nmap -sCV -T4 "$1" -p- -v -oN nmap.out

# ffuf scan for fuzzing website
ffuf -k -c -u "$target/FUZZ" -w "$wordlist" -o "$outfile" "$@"

# ffuf scan for fuzzing for subdomains
ffuf -k -c -ac -u "$target" -H "Host: FUZZ.$host" -w "$wordlist" -o "$outfile" "$@"
```

As soon as a target is entered in the field, those 4 scans are started: nmap on the target, subdomains scan on the host and ffuf scan on the target url for files or directories.
![adding_target](https://raw.githubusercontent.com/TheLastOfEugenes/puf/master/resources/adding_target.png)

The progression is shown for nmap as raw output, for the fuzzing scans as a progress bar:
![progress_bar](https://raw.githubusercontent.com/TheLastOfEugenes/puf/master/resources/progress_bar.png)

## Presentation of results

Not only does the application create a file system to store the results, it also displays a tree-style presentation of the files so one can open them easily and offers a presentation of the results by handling json output to present the output of a ffuf scan:
![ffuf_results](https://raw.githubusercontent.com/TheLastOfEugenes/puf/master/resources/ffuf_results.png)

or the nmap scans and their XML output:
![nmap_results](https://raw.githubusercontent.com/TheLastOfEugenes/puf/master/resources/nmap_results.png)

On top of starting a scan, the app offers to start a scan via multiple ways:
- by clicking on a row of the json result
![nmap_row_clickable](https://raw.githubusercontent.com/TheLastOfEugenes/puf/master/resources/nmap_row_clickable.png)

When clicking on the row, a few options are being presented to the user: start a directories scan, start a files scan, start a web scan (being directory, files and subdirectories scan at the same time, useful when starting a scan on a newly found subdomain for example).

![web_scan_progress](https://raw.githubusercontent.com/TheLastOfEugenes/puf/master/resources/web_scan_progress.png)
- by clicking on a row of a nmap result
![json_row_clickable](https://raw.githubusercontent.com/TheLastOfEugenes/puf/master/resources/json_row_clickable.png)
- By clicking on the tree:
	- clicking on the target (identified by a computer icon) offers to start a nmap scan
	- clicking on the host (identified by a web icon) offers to start a subdomain scan using either http or https scheme
	- clicking on the service (identified by stacked squares and named scheme_port) offers to start either a web, files or directories scan, using either http or https
(target)
![target](https://raw.githubusercontent.com/TheLastOfEugenes/puf/master/resources/target_scan.png)
(host)
![host_scan](https://raw.githubusercontent.com/TheLastOfEugenes/puf/master/resources/host_scan.png)
(service)
![service_scan](https://raw.githubusercontent.com/TheLastOfEugenes/puf/master/resources/service_scan.png)
(other sevice)
![other_service_scan](https://raw.githubusercontent.com/TheLastOfEugenes/puf/master/resources/other_service_scan.png)


Once the scans have be ran, clicking on a file will open the file and allow the reading of it. The supported types are
- xml (for nmap scans)
- json (for ffuf scans)
- any (displayed raw in a tab)
(here is raw)
![open_file_raw](https://raw.githubusercontent.com/TheLastOfEugenes/puf/master/resources/open_file_raw.png)
(the display result)
![nmap_raw_result](https://raw.githubusercontent.com/TheLastOfEugenes/puf/master/resources/nmap_raw_result.png)

and, when clicking on any other supported file type:
![json_file_clickable](https://raw.githubusercontent.com/TheLastOfEugenes/puf/master/resources/json_file_clickable.png)


## Filtering

The other big functionnality of this tool is the ability to sort yourself the results of the scans.
Forget the shady auto sorting of ffuf (ok I'll admit it's a good one but still) become the master of your own files.

When clicking on a json file then "custom filter" the user will be prompted with a window with a few options. This window allows a user to enter himself the parameters of his filter:
- enable/disable smart-filtering (default: enabled)
- count of packages to activate smart filtering
- add response statuses to filter out (example: 404, 301)
- add content length to filter out (example: if all error responses have the length 1812, you can filter out all responses with length 1812)
- add words count filter.
![json_file_filter](https://raw.githubusercontent.com/TheLastOfEugenes/puf/master/resources/json_file_filter.png)

The smart filtering works as follow: files are gathered by status code, words counts, response's length. If more than 1000 (this limit can be modified using the input) results are in the same category then all these are filtered out, leaving only the ones that differ.

This filter is activated by default, filtering any result found through a ffuf scan into a new file `<file>_f.json`, opening it when the filtering is done.

## Misc

### Functionnalities
On top of this, the application offers other functionnalities:
- a flag appear on the right of xml and json results. If pressed, the whole row is marked red as a reminder this could be an interesting target.
![flag_row](https://raw.githubusercontent.com/TheLastOfEugenes/puf/master/resources/flag_row.png)

When a process has been started, if you wish to stop the process before it naturally ends, you can click on the red square next to the cross.
![kill_process](https://raw.githubusercontent.com/TheLastOfEugenes/puf/master/resources/kill_process.png)

### Other commands
As part of the package, in the `aliases` file, you will find the bash commands that allow using these commands without having to use the gui entirely, the output is still readable using cat or jq. The filtering function, on the other hand, hasn't been uploaded yet, it is reserved to the gui for now.

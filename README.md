# EBS-Analyzer

The EBS-Anaylzer analyzes usage data provided by the publisher.
The im is to provide a preselection of titles for further licencing based on the usage and prices of the individual titles.

It is written as a python3 application using the flask framework.

## Setup

### Clone project

```
$ git clone https://github.com/ETspielberg/ebslists
```


### Install requirements

The programme is written as python flask application. 
Necessary dependencies are listed in the requirements.txt and can be installed via

```
$ pip install -r requirements.txt
```

### Configuration

The configuration needs only the folder where the csv files with the usage data are stored.
To implement it into a microservice framework it can be configured to the upload directory of the system.
In any case, a subdirectory `/ebslists` is appended.

```
LIBINTEL_UPLOAD_DIR = "${USER_HOME}/.libintel/uploads"
```

## File format

The file containing the usage data needs to have the following columns.

```
ISBN; title; subject area; year; total usage; price; ...
```

### Start up

To start the application the virtual environment has to be activated.
After that some environmental parameters need to be set for the flask application.
For a development version the following code can be executed: 

```
./venv/Scripts/activate
$env:FLASK_APP="start.py"
$env:FLASK_ENV="development"
$env:LIBINTEL_SETTINGS = "${USER_HOME}\.libintel\config\ebslists.cfg"
python -m flask run
```

File is saved in the upload directory specified in the config file.

## Running an analysis

After the file has been uploaded (or is stored in the folder `${USER_HOME}/.libintel/uploads/ebslists/`)
an analysis is started using a HTTP POST request, for example using cURL:

```
curl -X POST -F 'filename='<filename> -F 'model=<model>' -F 'limit=<limit>' \
    -F 'mode=<mode>' http://<server.address>:<server.port>/ebslists
```
`<filename>` corresponds to the filename of the usage data, `<model>` is an identifier for the ebs model (e.g. ebs_publisher_year),
 `<limit>` is the price limit for the ebs model, `<mode>` selects one the following modes of analysis:
 
* `only_usage`: Ranking anhand der Nutzung
* `only_cost_per_usage`: Ranking anhand Preis pro Nutzung
* `price_normalized_percentiles`: Ranking sowohl anhand von Preis und Preis pro Nutzung. Die beiden Teillisten werden auf den gleichen Wert normalisiert.
* `percentage_normalized_percentiles`: Ranking sowohl anhand von Preis und Preis pro Nutzung. Die beiden Teillisten werden auf die gleiche Anzahl von Einträgen normalisiert.
* `usage_normalized_percentile`: Ranking sowohl anhand von Preis und Preis pro Nutzung. Die beiden Teillisten werden auf die gleiche Nutzung normalisiert.
* `index`: Summer der Indizes der Ranking Listen als Reihungsfaktor
* `value_weighting`: Produkt derr Wichtungsfaktoren
* `value_weighting_exponential`: Produkt der exponentiellen Wichtungsfaktoren


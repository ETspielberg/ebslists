from flask import Flask
from flask import request

import json
import csv

from model.EbsTitle import EbsTitle

app = Flask(__name__)
# app.config.from_object('yourapplication.default_settings')
app.config.from_envvar("LIBINTEL_SETTINGS")

location = app.config.get("LIBINTEL_UPLOAD_DIR") + "\\ebslists\\"


def set_bools(virtual_limit, ebs_titles):
    total_sum = 0
    selected_sum = 0
    ebs_titles.sort(key=lambda x: x.total_usage, reverse=True)
    for title in ebs_titles:
        total_sum += title.price
        title.selection_usage = (total_sum < virtual_limit)
    ebs_titles.sort(key=lambda x: x.price_per_usage, reverse=False)
    total_sum = 0
    for title in ebs_titles:
        total_sum += title.price
        title.selection_price_per_usage = (total_sum < virtual_limit)
        title.selection_final = title.selection_price_per_usage and title.selection_usage
        if title.selection_final:
            selected_sum += title.price
    return selected_sum


@app.route('/ebslists', methods=['POST'])
def ebslist():
    filename = request.form['filename']
    limit = float(request.form['limit'])
    virtual_limit = 1.5 * limit
    with open(location + filename, 'r') as csvfile:
        linereader = csv.reader(csvfile, delimiter=';')
        ebs_titles = []
        for row in linereader:
            try:
                title = row[0]
                subject_area = row[1]
                price = float(row[3])
                try:
                    year = int(row[4])
                except ValueError:
                    year = 1900
                total_usage = int(row[17])
                if total_usage != 0:
                    price_per_usage = price / total_usage
                else:
                    price_per_usage = price
                ebs_title = EbsTitle(title, subject_area, price, year, total_usage, price_per_usage, False, False, False)
                ebs_titles.append(ebs_title)
            except ValueError:
                print('no values')
    old_selected_sum = 0
    selected_sum = set_bools(virtual_limit, ebs_titles)
    step_differ = True
    while step_differ:
        difference = selected_sum - limit
        virtual_limit -= difference * 1.5
        old_selected_sum = selected_sum
        print('old selected sum: ' + str(old_selected_sum))
        selected_sum = set_bools(virtual_limit, ebs_titles)
        print('new selected sum: ' + str(selected_sum))
        if (selected_sum - old_selected_sum) == 0:
            step_differ = False
    with open(location + filename.replace(".csv", "") + "_out.csv", 'w', newline='') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=';',
                                quotechar='|', quoting=csv.QUOTE_MINIMAL)
        spamwriter.writerow(['Title', 'Subject area', 'price', 'year', 'total usage', 'price per usage', 'selected'])
        for item in ebs_titles:
            spamwriter.writerow([item.title, item.subject_area, str(item.price), str(item.year), str(item.total_usage), str(item.price_per_usage), str(item.selection_final)])
    json_string = json.dumps([ob.__dict__ for ob in ebs_titles])
    return str(selected_sum) + ' selected'

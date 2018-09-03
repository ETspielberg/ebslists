import csv
import json
import requests

from flask import Flask
from flask import request

from model.EbsTitle import EbsTitle

app = Flask(__name__)
# app.config.from_object('yourapplication.default_settings')
app.config.from_envvar("LIBINTEL_SETTINGS")

location = app.config.get("LIBINTEL_UPLOAD_DIR") + "\\ebslists\\"


def set_bools(virtual_limit, ebs_titles, ebs_model):
    total_sum = 0
    selected_sum = 0
    if (ebs_model == 'price_normalized_percentiles'):
        ebs_titles.sort(key=lambda x: x.totalUsage, reverse=True)
        for title in ebs_titles:
            total_sum += title.price
            title.selection_usage = (total_sum < virtual_limit)
        ebs_titles.sort(key=lambda x: x.pricePerUsage, reverse=False)
        total_sum = 0
        for title in ebs_titles:
            total_sum += title.price
            title.selection_price_per_usage = (total_sum < virtual_limit)
            title.selected = title.selection_price_per_usage and title.selection_usage
            if title.selected:
                selected_sum += title.price
                print(title.title)
            if title.price == 0:
                title.selected = True
    elif (ebs_model == 'normalized_percentiles'):
        ebs_titles.sort(key=lambda x: x.totalUsage, reverse=True)
        for title in ebs_titles:
            total_sum += title.price
            title.selection_usage = (total_sum < virtual_limit)
        ebs_titles.sort(key=lambda x: x.pricePerUsage, reverse=False)
        total_sum = 0
        for title in ebs_titles:
            total_sum += title.price
            title.selection_price_per_usage = (total_sum < virtual_limit)
            title.selected = title.selection_price_per_usage and title.selection_usage
            if title.selected:
                selected_sum += title.price
                print(title.title)
            if title.price == 0:
                title.selected = True
    elif (ebs_model == 'percentiles') :
        ebs_titles.sort(key=lambda x: x.totalUsage, reverse=True)
        for title in ebs_titles:
            total_sum += title.price
            title.selection_usage = (total_sum < virtual_limit)
        ebs_titles.sort(key=lambda x: x.pricePerUsage, reverse=False)
        total_sum = 0
        for title in ebs_titles:
            total_sum += title.price
            title.selection_price_per_usage = (total_sum < virtual_limit)
            title.selected = title.selection_price_per_usage and title.selection_usage
            if title.selected:
                selected_sum += title.price
                print(title.title)
            if title.price == 0:
                title.selected = True
    elif (ebs_model == 'only_usage'):
        ebs_titles.sort(key=lambda x: x.totalUsage, reverse=True)
        for title in ebs_titles:
            total_sum += title.price
            title.selection_usage = (total_sum < virtual_limit)
            title.selected = title.selection_usage;
            selected_sum += title.price
    elif (ebs_model == 'only_cost_per_usage'):
        ebs_titles.sort(key=lambda x: x.pricePerUsage, reverse=False)
        for title in ebs_titles:
            total_sum += title.price
            title.selection_price_per_usage = (total_sum < virtual_limit)
            title.selected = title.selection_price_per_usage
            selected_sum += title.price
    return selected_sum


@app.route('/ebslists', methods=['POST'])
def ebslist():
    filename = request.form['filename']
    ebs_model = request.form['ebsModel']
    limit = float(request.form['limit'])
    virtual_limit = 1.5 * limit
    ebs_titles = load_data(filename)
    old_selected_sum = 0
    selected_sum = set_bools(virtual_limit, ebs_titles)
    step_differ = True
    n_cycles = 0
    while step_differ:
        n_cycles +=1
        difference = selected_sum - limit
        virtual_limit -= difference * 0.8
        old_selected_sum = selected_sum
        selected_sum = set_bools(virtual_limit, ebs_titles, ebs_model)
        if (selected_sum - old_selected_sum) == 0:
            step_differ = False
        if n_cycles == 100:
            step_differ = False
    with open(location + filename.replace(".csv", "") + "_out.csv", 'w', newline='') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=';',
                                quotechar='|', quoting=csv.QUOTE_MINIMAL)
        spamwriter.writerow(['ISBN', 'Title', 'Subject area', 'price', 'year', 'total usage', 'price per usage', 'selected'])
        for item in ebs_titles:
            spamwriter.writerow([item.isbn, item.title, item.subjectArea, str(item.price), str(item.year), str(item.totalUsage), str(item.pricePerUsage), str(item.selected), ebs_model])
    # save_ebs_list(ebs_list)
    return str(selected_sum) + ' selected'


def load_data(filename):
    with open(location + filename, 'r') as csvfile:
        linereader = csv.reader(csvfile, delimiter=';')
        ebs_titles = []
        for row in linereader:
            try:
                isbn = row[0]
                title = row[1]
                subject_area = row[2]
                price = float(row[5])
                try:
                    year = int(row[3][-4:])
                except ValueError:
                    year = 0
                total_usage = int(row[4])
                if total_usage != 0:
                    price_per_usage = price / total_usage
                else:
                    price_per_usage = price
                ebs_title = EbsTitle(isbn, title, subject_area, price, year, total_usage, price_per_usage, False, False,
                                     False, ebs_model)
                ebs_titles.append(ebs_title)
            except ValueError:
                print('no values')

def save_ebs_list(ebs_titles):
    payload = json.dumps([ob.__dict__ for ob in ebs_titles])
    url = 'http://localhost:11200/ebsData/saveList'
    headers = {'content-type': 'application/json'}
    post = requests.post(url, data=payload, headers=headers)
    print(post.status_code)

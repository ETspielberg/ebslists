import csv
import json
import requests
import math
import os

from flask import Flask
from flask import request
import py_eureka_client.eureka_client as eureka_client
from statistics import mean

from model.EbsTitle import EbsTitle

app = Flask(__name__)
# app.config.from_object('yourapplication.default_settings')
app.config.from_envvar("LIBINTEL_SETTINGS")
your_rest_server_port = 5000
eureka_client.init_registry_client(eureka_server="http://localhost:8761/eureka",
                                app_name="ebs-analyzer",
                                instance_port=your_rest_server_port)

location = app.config.get("LIBINTEL_UPLOAD_DIR") + "\\ebslists\\"


@app.route('/ebslists', methods=['POST'])
def ebslist():
    if not os.path.exists(location):
        os.makedirs(location)

    # reading parameters from HTTP-request
    ebs_filename = request.form['filename']
    ebs_model = request.form['model']
    ebs_mode = request.form['mode']
    ebs_limit = float(request.form['limit'])

    # load the data from the data file in the upload directory
    ebs_titles = load_data(ebs_filename, ebs_model)

    # make the selection, i.e. set the boolean "selectected" and weighting factors if necessary
    selected_sum = make_selection(ebs_limit, ebs_titles, ebs_mode)

    # persist the results to the database in order to offer them to the fachref-assistant
    # persist_ebs_list(ebs_list)

    # save the results to a _out-file in the upload directory
    save_ebs_list_file(ebs_titles, ebs_filename, ebs_model, ebs_mode)
    return str(selected_sum) + ' selected'


def load_data(filename, ebs_model):
    with open(location + filename, 'r') as csvfile:
        linereader = csv.reader(csvfile, delimiter=';')
        if not os.path.exists(location + "\\" + ebs_model + "\\"):
            os.makedirs(location + "\\" + ebs_model + "\\")
        ebs_titles = []
        for row in linereader:
            try:
                isbn = row[0]
                title = row[1]
                if ";" in title:
                    title.replace(";", ".")
                subject_area = row[2]
                price_string = row[5]
                if "." in price_string:
                    price_string = price_string.replace(".", ",")
                try:
                    price = float(price_string)
                except ValueError:
                    price = 0
                try:
                    year = int(row[3][-4:])
                except ValueError:
                    year = 0
                total_usage_string = row[4]
                if "." in total_usage_string:
                    total_usage_string = total_usage_string.replace(".", "")
                total_usage = int(total_usage_string)
                if total_usage != 0:
                    cost_per_usage = price / total_usage
                else:
                    cost_per_usage = price
                ebs_title = EbsTitle(isbn, title, subject_area, price, year, total_usage, cost_per_usage, True, True,
                                     False, ebs_model, 1)
                ebs_titles.append(ebs_title)
            except ValueError:
                print('no values')
                print(row)
    return ebs_titles


def make_selection(ebs_limit, ebs_titles, ebs_mode):
    if 'only_usage' in ebs_mode:
        set_bools_usage_for_cost_limit(ebs_titles, ebs_limit)
        return get_price_for_selection(ebs_titles)
    elif 'only_cost_per_usage' in ebs_mode:
        set_bools_cost_per_usage_for_cost_limit(ebs_titles, ebs_limit)
        return get_price_for_selection(ebs_titles)
    elif 'price_normalized_percentiles' in ebs_mode:
        virtual_limit = 1.5 * ebs_limit
        set_bools_usage_for_cost_limit(ebs_titles, virtual_limit)
        set_bools_cost_per_usage_for_cost_limit(ebs_titles, virtual_limit)
        price_selected = get_price_for_selection(ebs_titles)
        step_differ = True
        n_cycles = 0
        while step_differ:
            n_cycles += 1
            difference = price_selected - ebs_limit
            virtual_limit -= difference * 0.8
            old_selected_sum = price_selected
            set_bools_usage_for_cost_limit(ebs_titles, virtual_limit)
            set_bools_cost_per_usage_for_cost_limit(ebs_titles, virtual_limit)
            price_selected = get_price_for_selection(ebs_titles)
            if (price_selected - old_selected_sum) == 0:
                step_differ = False
            if n_cycles == 100:
                step_differ = False
    elif 'percentage_normalized_percentiles' in ebs_mode:
        mean_price = mean(title.price for title in ebs_titles)
        number = ebs_limit // mean_price
        make_selection_for_usage_with_threshold(ebs_titles, number)
        make_selection_for_cost_per_usage_with_threshold(ebs_titles, number)
        price_selected = get_price_for_selection(ebs_titles)
        step_differ = True
        n_cycles = 0
        while step_differ:
            n_cycles += 1
            old_selected_sum = price_selected
            if price_selected != 0:
                fraction = float((price_selected - ebs_limit)) / float(price_selected)
            else:
                fraction = 2
            number = number * (1 - fraction)
            make_selection_for_usage_with_threshold(ebs_titles, int(number))
            make_selection_for_cost_per_usage_with_threshold(ebs_titles, int(number))
            price_selected = get_price_for_selection(ebs_titles)
            print(price_selected)
            if (price_selected - old_selected_sum) == 0:
                step_differ = False
            if n_cycles == 100:
                step_differ = False
    elif 'usage_normalized_percentiles' in ebs_mode:
        mean_usage = mean(title.total_usage for title in ebs_titles)
        mean_price = mean(title.price for title in ebs_titles)
        usage_threshold = int(ebs_limit/mean_price * mean_usage)
        set_bools_usage_for_usage_limit(ebs_titles, usage_threshold)
        set_bools_cost_per_usage_for_usage_limit(ebs_titles, usage_threshold)
        price_selected = get_price_for_selection(ebs_titles)
        print(price_selected)
        step_differ = True
        n_cycles = 0
        while step_differ:
            n_cycles += 1
            old_selected_sum = price_selected
            if price_selected != 0:
                fraction = float((price_selected - ebs_limit)) / (8* ebs_limit)
            else:
                fraction = 2
            usage_threshold = usage_threshold * (1 - fraction)
            set_bools_usage_for_usage_limit(ebs_titles, usage_threshold)
            set_bools_cost_per_usage_for_usage_limit(ebs_titles, usage_threshold)
            price_selected = get_price_for_selection(ebs_titles)
            print(price_selected)
            if (price_selected - old_selected_sum) == 0:
                step_differ = False
            if n_cycles == 100:
                step_differ = False
    elif 'index' == ebs_mode:
        set_position_for_usage(ebs_titles)
        set_position_for_cost_per_usage(ebs_titles)
        price_selected = get_price_for_list_with_factor(ebs_titles, ebs_limit)
    elif 'index_weighting' == ebs_mode:
        set_weighting_for_position_usage(ebs_titles)
        set_weighting_for_position_cost_per_usage(ebs_titles)
        price_selected = get_price_for_list_with_weighting(ebs_titles, ebs_limit)
    elif 'value_weighting' == ebs_mode:
        set_weighting_for_usage(ebs_titles)
        set_weighting_for_cost_per_usage(ebs_titles)
        price_selected = get_price_for_list_with_weighting(ebs_titles, ebs_limit)
    elif 'index_weighting_exponential' == ebs_mode:
        set_exponential_weighting_for_position_usage(ebs_titles)
        set_exponential_weighting_for_position_cost_per_usage(ebs_titles)
        price_selected = get_price_for_list_with_weighting(ebs_titles, ebs_limit)
    elif 'value_weighting_exponential' == ebs_mode:
        set_exponential_weighting_for_usage(ebs_titles)
        set_exponential_weighting_for_cost_per_usage(ebs_titles)
        price_selected = get_price_for_list_with_weighting(ebs_titles, ebs_limit)
    return price_selected


def persist_ebs_list(ebs_titles):
    payload = json.dumps([ob.__dict__ for ob in ebs_titles])
    url = 'http://localhost:11200/ebsData/saveList'
    headers = {'content-type': 'application/json'}
    post = requests.post(url, data=payload, headers=headers)
    print(post.status_code)


def save_ebs_list_file(ebs_titles, ebs_filename, ebs_model, ebs_mode):
    with open(location + "\\" + ebs_model + "\\" + ebs_filename.replace(".csv", "_") + ebs_mode + "_out.csv", 'w', newline='') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=';',
                                quotechar='|', quoting=csv.QUOTE_MINIMAL)
        spamwriter.writerow(['ISBN', 'Title', 'Subject area', 'price', 'year', 'total usage', 'price per usage', 'selected', 'EBS model ID', 'weighting factor'])
        for item in ebs_titles:
            spamwriter.writerow([item.isbn, '"' + item.title + '"', item.subject_area, str(item.price), str(item.year), str(item.total_usage), str(item.cost_per_usage), str(item.selected), ebs_model, str(item.weighting_factor)])


def set_bools_usage_for_cost_limit(ebs_titles, cost_limit):
    total_sum = 0
    ebs_titles.sort(key=lambda x: x.total_usage, reverse=True)
    for title in ebs_titles:
        total_sum += title.price
        title.selection_usage = (total_sum < cost_limit)


def set_bools_cost_per_usage_for_cost_limit(ebs_titles, cost_limit):
    total_sum = 0
    ebs_titles.sort(key=lambda x: x.cost_per_usage, reverse=False)
    for title in ebs_titles:
        total_sum += title.price
        title.selection_cost_per_usage = (total_sum < cost_limit)


def set_bools_usage_for_usage_limit(ebs_titles, usage_limit):
    total_sum = 0
    ebs_titles.sort(key=lambda x: x.total_usage, reverse=True)
    for title in ebs_titles:
        total_sum += title.total_usage
        title.selection_usage = (total_sum < usage_limit)


def set_bools_cost_per_usage_for_usage_limit(ebs_titles, usage_limit):
    total_sum = 0
    ebs_titles.sort(key=lambda x: x.cost_per_usage, reverse=False)
    for title in ebs_titles:
        total_sum += title.total_usage
        title.selection_cost_per_usage = (total_sum < usage_limit)


def set_position_for_usage(ebs_titles):
    ebs_titles.sort(key=lambda x: x.total_usage, reverse=True)
    for idx, val in enumerate(ebs_titles):
        val.weighting_factor += idx


def set_position_for_cost_per_usage(ebs_titles):
    ebs_titles.sort(key=lambda x: x.cost_per_usage, reverse=False)
    for idx, val in enumerate(ebs_titles):
        val.weighting_factor += idx


def set_weighting_for_usage(ebs_titles):
    max_usage = max(title.total_usage for title in ebs_titles)
    for title in ebs_titles:
        title.weighting_factor = title.weighting_factor * title.total_usage / max_usage


def set_weighting_for_cost_per_usage(ebs_titles):
    max_cost_per_usage = max(title.cost_per_usage for title in ebs_titles)
    for title in ebs_titles:
        title.weighting_factor = title.weighting_factor * float(max_cost_per_usage - title.cost_per_usage) / max_cost_per_usage


def set_weighting_for_position_usage(ebs_titles):
    ebs_titles.sort(key=lambda x: x.total_usage, reverse=False)
    for idx, val in enumerate(ebs_titles):
        val.weighting_factor = val.weighting_factor * float(idx - 1) / ebs_titles.__len__()


def set_weighting_for_position_cost_per_usage(ebs_titles):
    ebs_titles.sort(key=lambda x: x.cost_per_usage, reverse=True)
    for idx, val in enumerate(ebs_titles):
        val.weighting_factor = val.weighting_factor * float(idx - 1) / ebs_titles.__len__()


def set_exponential_weighting_for_usage(ebs_titles):
    mean_usage = mean(title.total_usage for title in ebs_titles)
    for title in ebs_titles:
        title.weighting_factor = title.weighting_factor * math.exp(float(title.total_usage-mean_usage)/mean_usage)


def set_exponential_weighting_for_cost_per_usage(ebs_titles):
    mean_cost_per_usage = mean(title.cost_per_usage for title in ebs_titles)
    for title in ebs_titles:
        title.weighting_factor = title.weighting_factor * math.exp(-title.cost_per_usage/mean_cost_per_usage)


def set_exponential_weighting_for_position_usage(ebs_titles):
    ebs_titles.sort(key=lambda x: x.total_usage, reverse=True)
    for idx, val in enumerate(ebs_titles):
        val.weighting_factor = val.weighting_factor * math.exp(-float(idx - 1) / ebs_titles.__len__())


def set_exponential_weighting_for_position_cost_per_usage(ebs_titles):
    ebs_titles.sort(key=lambda x: x.cost_per_usage, reverse=False)
    for idx, val in enumerate(ebs_titles):
        val.weighting_factor = val.weighting_factor * math.exp(-float(idx - 1) / ebs_titles.__len__())


def make_selection_for_usage_with_threshold(ebs_titles, threshold):
    total_sum = 0
    ebs_titles.sort(key=lambda x: x.total_usage, reverse=True)
    for idx, val in enumerate(ebs_titles):
        if idx < threshold:
            val.selection_usage = True
            total_sum += val.price
        else:
            val.selection_usage = False
    return total_sum


def make_selection_for_cost_per_usage_with_threshold(ebs_titles, threshold):
    total_sum = 0
    ebs_titles.sort(key=lambda x: x.cost_per_usage, reverse=False)
    for idx, val in enumerate(ebs_titles):
        if idx < threshold:
            val.selection_cost_per_usage = True
            total_sum += val.price
        else:
            val.selection = False
    return total_sum


def get_price_for_selection(ebs_titles):
    total_sum = 0
    for title in ebs_titles:
        title.selected = title.selection_cost_per_usage and title.selection_usage
        if title.selected:
            total_sum += title.price
    return total_sum


def get_price_for_list_with_weighting(ebs_titles, limit):
    total_sum = 0
    ebs_titles.sort(key=lambda x: x.weighting_factor, reverse=True)
    for title in ebs_titles:
        if total_sum < limit:
            total_sum += title.price
            title.selected = True
        else:
            title.selected = False
    return total_sum


def get_price_for_list_with_factor(ebs_titles, limit):
    total_sum = 0
    ebs_titles.sort(key=lambda x: x.weighting_factor, reverse=False)
    for title in ebs_titles:
        if total_sum < limit:
            total_sum += title.price
            title.selected = True
        else:
            title.selected = False
    return total_sum

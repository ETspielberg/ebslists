import json

class EbsTitle:

    def __init__(self, isbn: str, title: str, subject_area: str, price: float, year: int, total_usage: int, cost_per_usage: float,
                 selection_usage: bool, selection_cost_per_usage: bool, selected: bool, ebs_model: str, weighting_factor: float):
        self.isbn = isbn
        self.title = title
        self.subject_area = subject_area
        self.price = price
        self.year = year
        self.total_usage = total_usage
        self.cost_per_usage = cost_per_usage
        self.selection_usage = selection_usage
        self.selection_cost_per_usage = selection_cost_per_usage
        self.selected = selected
        self.ebsModel = ebs_model
        self.id = self.ebsModel + "_" + self.isbn
        self.weighting_factor = weighting_factor

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)

import json

class EbsTitle:

    def __init__(self, title: str, subject_area: str, price: float, year: int, total_usage: int, price_per_usage: float,
                 selection_usage: bool, selection_price_per_usage: bool, selection_final: bool):
        self.title = title
        self.subject_area = subject_area
        self.price = price
        self.year = year
        self.total_usage = total_usage
        self.price_per_usage = price_per_usage
        self.selection_usage = selection_usage
        self.selection_price_per_usage = selection_price_per_usage
        self.selection_final = selection_final

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)

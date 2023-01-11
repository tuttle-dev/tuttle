from core.abstractions import SQLModelDataSourceMixin


class InvoicingDataSource(SQLModelDataSourceMixin):
    def __init__(self):
        super().__init__()

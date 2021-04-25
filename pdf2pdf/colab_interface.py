import re
from pathlib import Path as pathlib_Path
from urllib.request import pathname2url as urllib_pathname2url

from google.colab import auth
import gspread
from oauth2client.client import GoogleCredentials
import pandas as pd

from .params import Cols, Paths
from .db_utils import Db, setup_local_table
from .dataio import GenericData, Regaletiketten3X8YverData


class ColabInterface(object):

    def __init__(self, db_search=True, web_search=True, worksheet=None):
        self._curr_data_obj = GenericData(dict())
        self._df_dict = dict()
        self._df = pd.DataFrame.from_dict(self._df_dict)
        self._filnr = None
        with open(Paths.DB_CONF_PATH, mode='r') as f:
            for line in f.readlines():
                if re.match(r'FILNR=fil_[0-9]{3}$', line.strip()):
                    _, self._filnr = line.strip().split('=')
        Db.db_uri = f'file:{urllib_pathname2url(Paths.DB_PATH)}?mode=rw'
        if db_search:
            self._db_search = setup_local_table(filnr=self._filnr)
        else:
            self._db_search = db_search
        self._web_search = web_search
        self._worksheet = worksheet
        if worksheet and isinstance(worksheet, bool):
            auth.authenticate_user()
            gc = gspread.authorize(GoogleCredentials.get_application_default())
            self._worksheet = gc.open(Paths.SHEET).sheet1
        self._ws_rng = f"A2:{chr(ord('A')+len(GenericData.types)-1)}{{}}"
        if self._worksheet:
            self.clear_sheet()

    def update_df(self, data_obj=None, df_dict=None, **kwargs):
        if self._worksheet and df_dict:
            df_dict = self.read_from_sheet(max(map(len, df_dict.values())))
        self._curr_data_obj = data_obj(df_dict=df_dict, **kwargs)
        self._df_dict = self._curr_data_obj.df_dict
        self._df = pd.DataFrame.from_dict(self._df_dict)
        if self._worksheet:
            self.write_to_sheet()
        return self._df

    def undo_df(self, data_obj):
        data_obj.child = None
        self._curr_data_obj = data_obj
        self._df_dict = data_obj.df_dict
        self._df = pd.DataFrame.from_dict(self._df_dict)
        if self._worksheet:
            self.clear_sheet()
            self.write_to_sheet()
        return self._df

    def create_pdfs(self):
        if self._worksheet:
            self._df_dict = self.read_from_sheet(max(map(len, self._df_dict.values())))
        data = GenericData(self._df_dict)
        pages = data.to_pdf(self._df_dict, db_search=self._db_search)
        for key in pages.keys():
            if pages[key]:
                pdf_path = pathlib_Path(Paths.BASE_PATH) / f'{key}_Schilder.pdf'
                p1 = pages[key].pop(0)
                p1.save(pdf_path, 'PDF' ,resolution=50.0, save_all=True, append_images=pages[key])
                pages[key].insert(0, p1)
        return pages

    def read_from_sheet(self, rows):
        response = self._worksheet.get_all_values()[1:]
        keys = GenericData.types.keys()
        df_dict = {key: [] for key in keys}
        for col, key in enumerate(keys):
            for row in range(rows):
                value = response[row][col]
                if key == Cols.ARTNR:
                    value = int(value)
                elif key == Cols.STATT or key == Cols.PREIS:
                    value = value or '0'
                    value = float(value.replace(',', '.'))
                elif key in GenericData.to_pdf_registry.keys():
                    if value.strip() == 'TRUE':
                        value = True
                    else:
                        value = False
                df_dict[key].append(value)
        return df_dict

    def write_to_sheet(self):
        values = sum(self._df.values.tolist(), [])
        rows, _ = self._df.shape
        cell_list = self._worksheet.range(self._ws_rng.format(rows+1))
        for index, cell in enumerate(cell_list):
            cell.value = values[index]
        response = self._worksheet.update_cells(cell_list)
        print(Paths.SHEET_PATH + response['spreadsheetId'])

    def clear_sheet(self):
        cell_list = self._worksheet.range(self._ws_rng.format(100))
        for cell in cell_list:
            cell.value = ''
        self._worksheet.update_cells(cell_list)

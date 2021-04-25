import re
import sys

from PIL import Image as PIL_Image
from PIL import ImageDraw as PIL_ImageDraw
from PIL import ImageFont as PIL_ImageFont

from .params import Cols, Paths
from .pdfio import Regaletiketten3X8YverDataFromPdf
from .sanity_checks import SanityTests, sanitize_data_decorator
from .db_utils import read_from_db_decorator, write_to_db_decorator
from .web_utils import ForstingerProduktSoup

def preis_helper(preis):
    preis = format(float(preis), '.2f')
    preis = str(preis).replace('.', ',')
    if len(preis.split(',')[0]) >= 4:
        preis = f'{preis[:-6]}.{preis[-6:]}'
    if preis.split(',')[1] == '00':
        preis = f"€ {preis.split(',')[0]},-"
    else:
        preis = f'€ {preis}'
    return preis

def index_helper(string='', length=0):
    string = ''.join([i for i in string if not i.isspace()])
    if not string:
        string = '0'
    else:
        if not re.match('^[0-9]+(?:[,-][0-9]+)*$', string):
            raise Exception('Nicht gut!')                                             # TODO! Exception!
    indices = string.split(',')
    ranges = [i.split('-') for i in indices if not i.isnumeric()]
    indices = set(int(i) for i in indices if i.isnumeric())
    for i in ranges:
        lower, upper = int(i[0]), int(i[1])
        if len(i) > 2 or lower >= upper:
            raise Exception('Nicht gut!')                                             # TODO! Exception!
        else:
            indices.update(range(lower, upper+1))
    if max(indices) > length:
        raise Exception('Nicht gut!')                                               # TODO! Exception!
    return sorted(indices)


class GenericData(SanityTests):

    global_vars = {}
    to_pdf_registry = {}
    types = {Cols.ARTTEXT1: '', 
            Cols.ARTTEXT2: '', 
            Cols.ARTNR: 0, 
            Cols.STATT: 0, 
            Cols.PREIS: 0}

    def __init_subclass__(cls, **kwargs):
        cls._name = kwargs.get('_name', cls.__name__)
        if cls.__dict__.get('from_pdf'):
            if not getattr(sys.modules[__name__], f'{cls.__name__}FromPdf'):
                raise NotImplementedError
        if cls.__dict__.get('to_pdf'):
            GenericData.types[cls._name] = False
            GenericData.to_pdf_registry[cls._name] = cls
        super().__init_subclass__()

    @read_from_db_decorator
    @sanitize_data_decorator
    def __init__(self, df_dict, *args, parent=None, **kwargs):
        self.df_dict = df_dict
        self.child = None
        if parent:
            self.parent = parent
            self.parent.child = self

    @classmethod
    def edit_df(cls, *args, user_input=None, parent=None, 
            df_dict=None, index=None, **kwargs):
        if not df_dict:
            raise Exception('Holla, holla!')                                          # TODO! Exception!
        user_input = user_input or dict()
        user_input = {key: user_input[key] for key in user_input if key in cls.types and user_input[key]}
        r = index_helper(index, max(map(len, df_dict.values()))-1)
        for key in cls.types:
            for i in r:
                df_dict[key][i] = user_input.get(key, df_dict[key][i])
        return cls(df_dict, parent=parent)

    @classmethod
    def from_input(cls, *args, user_input=None, parent=None, 
            df_dict=None, **kwargs):
        user_input = user_input or dict()
        df_dict = df_dict or {key: [] for key in cls.types}
        for key in cls.types:
            df_dict[key].append(user_input.get(key, cls.types[key]))
        return cls(df_dict, parent=parent)

    @classmethod
    def from_pdf(cls, *args, **kwargs):
        raise NotImplementedError

    @classmethod
    def from_web(cls, *args, user_input=None, parent=None, soup=None, 
            db_search=True, web_search=True, df_dict=None, artnr=None, **kwargs):
        if not artnr:
            raise Exception('Bruder, gib mir eine Artnr.!')                           # TODO! Exception!
        if not db_search and not web_search:
            raise Exception('Du hast die Suchfunktion deaktiviert!')                  # TODO! Exception!
        req = [i for i in (*cls.to_pdf_registry, Cols.ARTNR)]
        user_input = user_input or dict()
        user_input = {key: user_input[key] for key in user_input if key in req}
        df_dict = df_dict or {key: [] for key in cls.types}
        if web_search:
            soup = ForstingerProduktSoup(artnr)
        rstart = max(map(len, df_dict.values()))-1
        for key in cls.types:
            if key in user_input.keys():
                df_dict[key].append(user_input[key])
            else:
                find = getattr(soup, f'find_{key.lower()}', lambda i: i)
                df_dict[key].append(find(cls.types[key]))
        r = range(rstart+1, rstart, -1)
        return cls(df_dict, parent=parent, db_search=db_search, r=r, sanitize=True)

    @write_to_db_decorator
    def to_pdf(self, *args, df_dict=None, **kwargs):
        if not df_dict:
            raise Exception('Du hast nix eingespielt!')                               # TODO! Exception!
        pages = {cls_name: [] for cls_name in self.to_pdf_registry.keys()}
        cnt = {cls_name: 0 for cls_name in self.to_pdf_registry.keys()}
        keys = set(self.types.keys()) - set(self.to_pdf_registry.keys())
        for index in range(max(map(len, df_dict.values()))):
            for cls_name in self.to_pdf_registry.keys():
                if df_dict[cls_name][index]:
                    cls = self.to_pdf_registry.get(cls_name)
                    if not cnt[cls_name] % cls.max_tags:
                        pages[cls_name].append(PIL_Image.new('RGB', cls.dim, (255, 255, 255)))
                    insert_text = PIL_ImageDraw.Draw(pages[cls_name][-1])
                    cls.to_pdf(df_dict, index, keys, insert_text, cnt[cls_name])
                    cnt[cls_name] += 1
        return pages


class Regaletiketten3X8YverData(GenericData):

    @classmethod
    def from_pdf(cls, *args, user_input=None, parent=None, df_dict=None, 
            db_search=True, **kwargs):
        user_input = user_input or dict()
        user_input = {key: user_input[key] for key in user_input if key in cls.to_pdf_registry}
        df_dict = df_dict or {key: [] for key in cls.types}
        rstart = max(map(len, df_dict.values()))-1
        tags = getattr(sys.modules[__name__], f'{cls.__name__}FromPdf')()
        for tag in tags:
            for key in cls.types:
                if key in user_input.keys():
                    df_dict[key].append(user_input.get(key, cls.types[key]))
                else:
                    extract = getattr(tags, f'extract_{key.lower()}', lambda i,j: j)
                    df_dict[key].append(extract(tag, cls.types[key]))
        rstop = max(map(len, df_dict.values()))-1
        r = range(rstop, rstart, -1)
        return cls(df_dict, parent=parent, db_search=db_search, r=r)


class Preisschilder2X2YhorData(GenericData, _name='A6'):

    dim = (3508, 2480)
    margin = 165
    offset = ((0, 0), (0, 1240), (1754, 0), (1754, 1240))
    fonts = {Cols.ARTTEXT1: PIL_ImageFont.truetype(Paths.SUSE_SANS_BOLD, 95), 
            Cols.ARTTEXT2: PIL_ImageFont.truetype(Paths.SUSE_SANS, 70), 
            Cols.ARTNR: PIL_ImageFont.truetype(Paths.SUSE_SANS, 45), 
            Cols.STATT: PIL_ImageFont.truetype(Paths.SUSE_SANS, 45), 
            Cols.PREIS: PIL_ImageFont.truetype(Paths.SUSE_SANS_BOLD, 118)}
    yaxis = {Cols.ARTTEXT1: 508, 
            Cols.ARTTEXT2: 635, 
            Cols.ARTNR: 750, 
            Cols.STATT: 915, 
            Cols.PREIS: 985}
    max_tags = 4

    @classmethod
    def to_pdf(cls, df_dict, index, keys, insert_text, cnt, *args, **kwargs):
        cnt = cnt % cls.max_tags
        for key in keys:
            func = getattr(cls, f'insert_{key.lower()}')
            func(insert_text, key, df_dict[key][index], cnt)

    @classmethod
    def insert_arttext1(cls, insert_text, key, value, index, *args, **kwargs):
        x, y = cls.offset[index]
        koords = (cls.margin+x, cls.yaxis[key]+y)
        arttext1 = ' '.join([line.strip() for line in value.split('$')])
        insert_text.text(koords, arttext1, (0, 0, 0), font=cls.fonts[key])

    @classmethod
    def insert_arttext2(cls, insert_text, key, value, index, *args, **kwargs):
        x, y = cls.offset[index]
        koords = (cls.margin+x, cls.yaxis[key]+y)
        arttext2 = ' '.join([line.strip() for line in value.split('$')])
        insert_text.text(koords, arttext2, (0, 0, 0), font=cls.fonts[key])

    @classmethod
    def insert_artnr(cls, insert_text, key, value, index, *args, **kwargs):
        x, y = cls.offset[index]
        koords = (cls.margin+x, cls.yaxis[key]+y)
        insert_text.text(koords, f'Artnr.: {value}', (0, 0, 0), font=cls.fonts[key])

    @classmethod
    def insert_statt(cls, insert_text, key, value, index, *args, **kwargs):
        x, y = cls.offset[index]
        koords = (cls.margin+x, cls.yaxis[key]+y)
        if not value:
            insert_text.text(koords, 'Jetzt nur:', (0, 0, 0), font=cls.fonts[key])
        else:
            value = preis_helper(value)
            insert_text.text(koords, f'Statt: {value}', (0, 0, 0), font=cls.fonts[key]) 

    @classmethod
    def insert_preis(cls, insert_text, key, value, index, *args, **kwargs):
        x, y = cls.offset[index]
        koords = (cls.margin+x, cls.yaxis[key]+y)
        value = preis_helper(value)
        insert_text.text(koords, value, (0, 0, 0), font=cls.fonts[key])


class Preisschilder1X1YverData(GenericData, _name='A4'):

    dim = (2480, 3508)
    margin = 185
    fonts = {Cols.ARTTEXT1: PIL_ImageFont.truetype(Paths.SUSE_SANS_BOLD, 165), 
            Cols.ARTTEXT2: PIL_ImageFont.truetype(Paths.SUSE_SANS, 110), 
            Cols.ARTNR: PIL_ImageFont.truetype(Paths.SUSE_SANS, 45), 
            Cols.STATT: PIL_ImageFont.truetype(Paths.SUSE_SANS, 100), 
            Cols.PREIS: PIL_ImageFont.truetype(Paths.SUSE_SANS_BOLD, 280)}
    yaxis = {Cols.ARTTEXT1: [1700, 1900], 
            Cols.ARTTEXT2: [2120, 2250], 
            Cols.ARTNR: 2420, 
            Cols.STATT: 2780, 
            Cols.PREIS: 2950}
    max_tags = 1

    @classmethod
    def to_pdf(cls, df_dict, index, keys, insert_text, *args, **kwargs):
        for key in keys:
            func = getattr(cls, f'insert_{key.lower()}')
            func(insert_text, key, df_dict[key][index])

    @classmethod
    def insert_arttext1(cls, insert_text, key, value, *args, **kwargs):
        koords = [(cls.margin, i) for i in cls.yaxis[key]]
        arttext1 = value.split('$', maxsplit=1)
        for i, line in enumerate(arttext1[::-1]):
            insert_text.text(koords[i-1], line.strip(), (0, 0, 0), font=cls.fonts[key])

    @classmethod
    def insert_arttext2(cls, insert_text, key, value, *args, **kwargs):
        koords = [(cls.margin, i) for i in cls.yaxis[key]]
        arttext2 = value.split('$', maxsplit=1)
        for i, line in enumerate(arttext2):
            insert_text.text(koords[i], line.strip(), (0, 0, 0), font=cls.fonts[key])

    @classmethod
    def insert_artnr(cls, insert_text, key, value, *args, **kwargs):
        koords = (cls.margin, cls.yaxis[key])
        insert_text.text(koords, f'Artnr.: {value}', (0, 0, 0), font=cls.fonts[key])

    @classmethod
    def insert_statt(cls, insert_text, key, value, *args, **kwargs):
        koords = (cls.margin, cls.yaxis[key])
        if not value:
            insert_text.text(koords, 'Jetzt nur:', (0, 0, 0), font=cls.fonts[key])
        else:
            value = preis_helper(value)
            insert_text.text(koords, f'Statt: {value}', (0, 0, 0), font=cls.fonts[key]) 

    @classmethod
    def insert_preis(cls, insert_text, key, value, *args, **kwargs):
        koords = (cls.margin, cls.yaxis[key])
        value = preis_helper(value)
        insert_text.text(koords, value, (0, 0, 0), font=cls.fonts[key]) 

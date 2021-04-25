import re

from pdfminer.high_level import extract_pages as pdfminer_extract_pages
from pdfminer.layout import LTTextBoxHorizontal as pdfminer_LTTextBoxHorizontal

from .params import Paths


class GenericDataFromPdf(object):

    _coln = None
    _rown = None

    def __init_subclass__(cls, **kwargs):
        if not cls._coln or not cls._rown:
            raise NotImplementedError
        super().__init_subclass__()

    def __init__(self):
        self.tags = []
        for page in pdfminer_extract_pages(Paths.PDF_PATH):
            *_, coldim, rowdim = page.bbox
            coldim, rowdim = coldim/self._coln, rowdim/self._rown
            matrix = [[[] for _ in range(self._coln)] for _ in range(self._rown)]
            items = [i for i in page if isinstance(i, pdfminer_LTTextBoxHorizontal)]
            for item in items:
                row, col = int(item.y0//rowdim), int(item.x0//coldim)
                matrix[row][col].append(item)
            self.tags.extend([tag for row in matrix for tag in row if tag])

    def __len__(self):
        return len(self.tags)

    def __getitem__(self, index):
        return self.tags[index]


class Regaletiketten3X8YverDataFromPdf(GenericDataFromPdf):

    _coln = 3
    _rown = 8
    _arttext_font_size = range(9, 12)
    _preis_font_size = range(25, 30)

    def __init__(self):
        super().__init__()

    def extract_text(self, tag):
        for index, e in enumerate(tag):
            for line in e:
                if int(line.height) in self._arttext_font_size:
                return tag.pop(index).get_text().strip('\n')
        return ''

    def extract_arttext1(self, tag, *args, **kwargs):
        return self.extract_text(tag)

    def extract_arttext2(self, tag, *args, **kwargs):
        return self.extract_text(tag)

    def extract_artnr(self, tag, *args, **kwargs):
        for i in tag:
            artnr = re.search('[12][0-9]{7}', i.get_text())
            if artnr:
                return int(artnr.group(0))
        return 0

    def extract_preis(self, tag, *args, **kwargs):
        for index, e in enumerate(tag):
            for line in e:
                if int(line.height) in self._preis_font_size:
                    preis = e.get_text().replace('.', '').strip('\n')
                    return float(preis.replace(',', '.'))
        return 0

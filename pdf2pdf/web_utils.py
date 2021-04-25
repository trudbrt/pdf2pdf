import re
from urllib.request import urlopen as urllib_urlopen

import bs4 as bs


class GenericSoup(object):

    soup_registry = {}

    def __init_subclass__(cls, **kwargs):
        GenericSoup.soup_registry[cls.__name__] = cls
        super().__init_subclass__()


class ForstingerProduktSoup(GenericSoup):

    def __init__(self, target):
        self.artnr = target
        url = f'https://www.forstinger.com/index.php?cl=search&searchparam={target}'
        try:
            target = urllib_urlopen(url)
        except:
            target = ''
        soup = bs.BeautifulSoup(target, 'lxml')
        in_webshop = soup.find('div', class_='headline')
        if in_webshop and re.match('[^0]* Treffer', in_webshop.text.strip()):
            self.soup = soup
        else:
            self.soup = None

    def find_arttext1(self, reqtype, *args, **kwargs):
        if self.soup:
        arttext1 = self.soup.find('h5', class_='product_card-headline')
        if arttext1:
            return arttext1.text.strip()
        return reqtype

    def find_artnr(self, *args, **kwargs):
        return self.artnr

    def find_statt(self, reqtype, *args, **kwargs):
        if self.soup:
            statt = self.soup.find('div', class_='product_card-price')
        if statt:
            statt = [float(i)/100 for i in statt.text.split('statt')]
            if len(statt) > 1:
                return statt[-1]
        return reqtype

    def find_preis(self, reqtype, *args, **kwargs):
        if self.soup:
            preis = self.soup.find('div', class_='product_card-price')
            if preis:
                return [float(i)/100 for i in preis.text.split('statt')][0]
        return reqtype

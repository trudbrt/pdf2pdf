import re


class SanityTests(object):

    @staticmethod
    def sanitize_arttext1(arttext1):
        return bool(arttext1)

    @staticmethod
    def sanitize_arttext2(arttext2):
        return bool(arttext2)

    @staticmethod
    def sanitize_artnr(artnr):
        return bool(re.match('[12][0-9]{7}$', str(artnr).strip()))

    @staticmethod
    def sanitize_preis(preis):
        return float(preis) > 0


def sanitize_data_decorator(func):
    def sanitize_data_wrapper(*args, **kwargs):
        msgs = []
        obj, df_dict, *args = args
        for key in df_dict:
            test = getattr(obj, f'sanitize_{key.lower()}', lambda i: True)
            for i, e in enumerate(df_dict[key]):
                if not test(e):
                    msgs.append((i, key, e))
        for index, key, value in sorted(msgs):
            print(f'Eintrag {index:3}: {value:>12} ungültig als {key}!')
        return func(obj, df_dict, *args, **kwargs)
    return sanitize_data_wrapper

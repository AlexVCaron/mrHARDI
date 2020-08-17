import json
import re


class MagicConfigEncoder(json.JSONEncoder):
    def default(self, o):
        try:
            return dict(o)
        except TypeError:
            return repr(o)

    def encode(self, o):
        def json2py(match):
            substr = match.string
            subs = {1: "True", 2: "False", 3: "None"}
            for g, _ in filter(
                lambda kv: kv[1] is not None,
                zip(range(1, len(subs) + 1), match.groups())
            ):
                start, end = match.span(g)
                substr = substr[:start] + subs[g] + substr[end:]

            return substr[match.start():match.end()]

        string = super().encode(o)
        p = re.compile(r'[,\n\s]*(true)|(false)|(null)[,\n\s]*')

        return p.sub(json2py, string)

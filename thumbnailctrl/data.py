import io
import zlib

import wx
import wx.lib.embeddedimage as embed


def getDataSH():
    """Return the first part of the shadow dropped behind thumbnails."""
    return zlib.decompress(
        b'x\xda\xeb\x0c\xf0s\xe7\xe5\x92\xe2b``\xe0\xf5\xf4p\t\x02\xd2_A\x98\x83\rHvl'
        b'\xdc\x9c\n\xa4X\x8a\x9d<C8\x80\xa0\x86#\xa5\x83\x81\x81y\x96\xa7\x8bcH\xc5'
        b'\x9c\xb7\xd7\xd7\xf6\x85D2\xb4^\xbc\x1b\xd0\xd0p\xa6\x85\x9d\xa1\xf1\xc0\xc7'
        b'\x7f\xef\x8d\x98\xf89_:p]\xaew\x0c\xe9\x16[\xbc\x8bSt\xdf\x9aT\xad\xef\xcb'
        b'\x8e\x98\xc5\xbf\xb3\x94\x9ePT\xf8\xff\xf7\xfbm\xf5\xdb\xfeZ<\x16{\xf01o[l'
        b'\xee\xee\xbd7\xbe\x95\xdd\xde\x9d+\xbf\xfdo\xf9\xb9\xd0\x03\x8be\xb7\xc7\xe6'
        b'Y\xcb\xbd\x8b\xdfs\xe3[\xd6\xed\xe5\x9b}\x99\xe6=:\xbd\xed\xfc\xedu|\xfcq'
        b'\xfb\xec/K<\xf8\xfec\xd7\xdb\xdb\x87W\xec\xcf\xfd]\xb0\xcc\xf0\xc0\xe5=\xf7^'
        b'\x1e\xf9\xfb\xe6\xe6\xce\xe9\x0c\xfb\xa7\xafPt\xbb"\xa0\x9c\xd5!hz\xa4C*\xc9'
        b'\x85\xd7pQ\x9bD\xa0s\xcf\xa8\xf0\xa8\xf0\x00\x0b\x9fyX\x7fo\xef\xdf\xc7\xda'
        b'\r\xcbw\xd4\xfcx\xe0\xcdk\xd8\x9e[~{\xdd\xf6\xbfw\xbe\xfd\xddS\xdc\xe0\xfec_'
        b'\xf0\xfe\xeb\xb7\xdf\xf1\xdd\xce\xdb&\xbb\xbdv\xe7\xff\xc3\xaf\x8dy\x99\xe5'
        b'\x9e?\xf7\xfb+\xb7\xfdnLN\xf5\xc6\xb7g\xfd\xca_\x9a\x7f?\x7f\xe0\xfe\xe3\xaa'
        b'\xe5\x0b\xf4\xb7\xcb\xea\x97\xed\n\xb7\xbf\xff\xadh\xf9\xe3\x1d\xd5f\x7fb'
        b'\xdf\x95Y\x15\xc6\xe7\xee\xfe\xcbz7Y\xbd\xde[\xf3y\x1f0\xd72x\xba\xfa\xb9'
        b'\xacsJh\x02\x00\xc4i\x8dN'
    )


def getDataBL():
    """Return the second part of the shadow dropped behind thumbnails."""
    return zlib.decompress(
        b'x\xda\xeb\x0c\xf0s\xe7\xe5\x92\xe2b``\xe0\xf5\xf4p\t\x02\xd2\xac \xcc\xc1'
        b"\x06${\xf3\xd5\x9e\x02)\x96b'\xcf\x10\x0e \xa8\xe1H\xe9\x00\xf2\xed=]\x1cC8f"
        b'\xea\x9e\xde\xcb\xd9` \xc2\xf0P\xdf~\xc9y\xaeu\x0f\xfe1\xdf\xcc\x14\x1482A'
        b'\xe9\xfd\x83\x1d\xaf\x84\xac\xf8\xe6\\\x8c3\xfc\x98\xf8\xa0\xb1\xa9K\xec\x9f'
        b'\xc4\xd1\xb4GG{\xb5\x15\x8f_|t\x8a[a\x1fWzG\xa9\xc4,\xa0Q\x0c\x9e\xae~.\xeb'
        b'\x9c\x12\x9a\x00\x7f1,7'
    )


def getDataTR():
    """Return the third part of the shadow dropped behind thumbnails."""
    return zlib.decompress(
        b'x\xda\xeb\x0c\xf0s\xe7\xe5\x92\xe2b``\xe0\xf5\xf4p\t\x02\xd2\xac \xcc\xc1'
        b'\x06${\xf3\xd5\x9e\x02)\x96b\'\xcf\x10\x0e \xa8\xe1H\xe9\x00\xf2m=]\x1cC8f'
        b'\xe6\x9e\xd9\xc8\xd9` \xc2p\x91\xbd\xaei\xeeL\x85\xdcUo\xf6\xf7\xd6\xb2\x88'
        b'\x0bp\x9a\x89i\x16=-\x94\xe16\x93\xb9!\xb8y\xcd\t\x0f\x89\n\xe6\xb7\xfcV~6'
        b'\x8dFo\xf5\xee\xc8\x1fOaw\xc9\x88\x0c\x16\x05\x1a\xc4\xe0\xe9\xea\xe7\xb2'
        b'\xce)\xa1\t\x00"\xf9$\x83'
    )


def getShadow():
    """Creates a shadow behind every thumbnail."""
    sh_tr = wx.Image(io.BytesIO(getDataTR())).ConvertToBitmap()
    sh_bl = wx.Image(io.BytesIO(getDataBL())).ConvertToBitmap()
    sh_sh = wx.Image(io.BytesIO(getDataSH())).Rescale(500, 500, wx.IMAGE_QUALITY_HIGH)
    return (sh_tr, sh_bl, sh_sh.ConvertToBitmap())


_FILE_BROKEN = embed.PyEmbeddedImage(
    b'iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAABGdBTUEAAK/INwWK6QAADU9JREFUeJzNW'
    b'n1QE2cefja7yRI+lAKiAgKCVIqegUYMFMsM4kfvzk7nmFrnvHGcOT3bq3P/OJ1pb+zYf+r0HGxt6VVFqp'
    b'YqWq9TW23RVnp6R7FXiq0UPAGhyFeQSCQJISHZ7Mf9gZuGkE02IeA9M5k3u/vuu+/z/H7v7/297y4BPzh'
    b'//vxfSJIsIgjC5a/eTIPn+UnHgiDIqisIAsUwTNfmzZtfA8D7qk/5e3B0dPS6wsLCp/09MFTIbdO7ntR9'
    b'vs5HRESgvr6+E0AlAD2AKZX8CsDzvEKtVsvqaKjw7LggCO7jcJQqlQoMw6gBpAIYRAgCECGxCgDPTsohE'
    b'opI4n+e5xXww1MRHkry4d1Zf9fkuv90MOsCeMKfGN51pO6ZrmizKsBsWt976EjhoQ+BYMQItpSDWRNAjp'
    b'tPZ4xLCfl/PQTCaX2p+wNhVgSYbet7tumdRXpj1ofAbFhfqn1fmHEBHpb1AYAgAudxMy4AQRB+LReuSB/'
    b'MGsETMyqA2WyG1WqVZQl/CDUZeuge0NvbKwwODk7bC7zryYFI/qF6QGNj42BnZ6dZ6rocQtNNhQNhxgQw'
    b'Go24fPnyDy0tLTcFQfDpBZ7/w2198RcIMyZAW1vb+KVLlxoGBwfr7927B4Vi8qO8CfnqbCjWD4Y8MEMCC'
    b'IKA77777me73d7a1tb25dDQkNXzmud/giDgdDrBsqzkuA1l7CuVSgCA0+n0y3FGBBgYGMCVK1eub926dR'
    b'FN04aBgYH/el73JKRUKjE4OIi+vj5QFDWtaVG0fGRkJHiex7lz5xynT59uBMBI9TWsAoidaW1tNTc1Nd1'
    b'cv379zuzs7F91dHT8x+l0TooDnuju7h779ttvjdOdLlUqFaKjo9HV1YX9+/d379q16+QXX3xxFsAAMHU7'
    b'DAgggNw1tQiCIOByuXDt2rWbK1asUOfk5KxMSUlZW19f39LX18eTJDmpbbG8cePGndra2mtDQ0NQKpUhJ'
    b'UPR0dHgeR6ffvqpbdeuXV+9/vrrR4eGhs4A+ArA3ZAECAXd3d24dOnSD2VlZavy8vKQmppaUFdXN2gwGO'
    b'561yVJEmazGR0dHV3nz5//+NatW0MU5XebcgooikJMTAy6urqwb9++zp07d1ZfvXq1GsAn8+bNa6qsrEy'
    b'GxJY4EGBTlCAIhVR0ZhgGTqcTTqcTDocDDocDgiDgm2++0Y+MjNxbuXLl7wmCQFpaWtbcuXMje3p6fly9'
    b'enWyeL8gCCBJEj09PUJLS0s7z/PXWlpavigoKNhBURRYlnU/S6qMjIwEwzD47LPPbIcOHWq4cuXKPwF8D'
    b'+DHF154QV1cXFxpsVjiAGwGYIUPL/ArgNFoNNbV1dmtVqvdarW6LBaLY2xszOFwOBiLxWKz2WxOs9lsHx'
    b'0ddZhMJpvZbB7v7u7+effu3elZWVmJAJCUlBS1bt26nNbW1kaj0fj0I4884iYHAHfu3Lnf2dnZDWC4oaH'
    b'hH08++eRWrVZLe9bxJk9RFNRqNTo6OvDhhx92Hj16tG5kZKQBwHUAneXl5cVarfaQVqtddurUqesAUgC0'
    b'BysAsWfPngOjo6ONY2NjUQzDOACMA7ADcGAisjoBuB6U4jFTWlp6Kj4+HjzPIzExEbm5uSuPHz9+csuWL'
    b'faEhIRIl8sFgiDA8zxu3rz585YtW3SpqanX9u7d+93GjRuv5eXlrRGvT+oQQUCtVsPhcODcuXO2w4cPi1'
    b'ZvAnADgP3EiRN7NBrNntzcXDXHcXA6nREAJF9u+BNA6OnpuQ1gGAD5gCjrUXIPFOUflAIA7siRI8Xp6ek'
    b'aYOI1lVKpRGZmpqatre2QXq/v1mg0y4EJKxoMBrS1tQ2UlJQ8abPZjAD23Lhx46Pi4uI1aWlp7mEl1qdp'
    b'Grdu3UJNTU1nVVVV3cjIyDUAPwJof+WVVzJ0Ol1NQUHBbxMTEyHOOoEQKOKMP/jJxoIFC/6QmZlJidYTB'
    b'AHp6emp2dnZCV1dXY0MwywnCAIkSUKv1zu7u7uNu3fvTh8aGtoE4Pj7779/ec2aNZ0ZGRlZwC9Wt9vt+P'
    b'zzz22VlZUNV69eFa3+EwDTkSNHynJyct5ZtWpVikKhgMPhgEKhkJx2gxFgSv1t27ZRUVFRFMuyZGZmZmJ'
    b'cXNwcpVIZT9N0tMvlWpiSklKmVConBbGkpCRq3bp1KxsbG69v3Lhxe3p6OgRBQHt7u2Hx4sVRycnJ9Ny5'
    b'czO3bdv2VHV19XvNzc2frF69+pXY2FgoFAopq3ds2rQp6plnnnkzLy9v99KlS8EwDDiOC2r5LSnAiRMnI'
    b'ubNm/dHkiSzaZqOIUkygabpGIqi4iiKmkuSZDRJkiqVSkWRJKmkaZqMiIhAZGQkOI5zk+c4DnFxccjOzt'
    b'ZWVVV9+eKLLw5nZGTMYxgGzc3Ndx577LGF8fHxiI2NhU6n+111dfWZixcvnispKfmzTqebe+HCBW+rtwK'
    b'4/8Ybb+RpNJojBQUFq2JiYuB0OgH8kgqLpdiXoAVobW2NfvbZZ/cWFhbOly3ngwf6yvczMzNzWJZV9Pb2'
    b'/lRUVLR2cHAQt2/fvrt9+3YtSZJQKBRYtmxZYXFx8ar6+vqrTU1NF7/++mtdZWXll0ajsQETQa4TE3HmB'
    b'Y1Gsz8/P3+Oy+Vyj3dP8nK9QFKA/v5+Cn7GfzBZmiAISE5OTiwqKsq4fft2k91uX9vf3283GAyWtLS0ZN'
    b'FTsrOzI0pKSsrq6+v//c477/xNr9evwMRr7ZsAhl966aUFOp3uzfz8/C2LFi3C+Pj4JMLeAsjJYiUFYFk'
    b'2oIRyReA4DikpKSgqKlpZW1t7saysjOvo6NAvXbo0NjExMZLneXAchzlz5kCj0TwVGxu7RK/Xt2Mihx8D'
    b'wBw4cGBDbm5uRWFh4aNKpRJ2u30S8VCsD8hYCwRzXqouz/OIiopCVlaWtrm5+X57e/tAS0uLPicnJzEhI'
    b'cE9TnmeR05OTvJzzz33a0xMtyNarVY4fvz4a6WlpRdKSkoeFZfPYpSXIi93SyzYWWASMTmlZ/2MjIys+P'
    b'j4mI6Ojoa+vj5h/fr1xaKrikIlJyfj8ccfLwNw7NVXX43TarV/LyoqWhsXF4fx8XF3TPFF2Pv/tPIAu93'
    b'ul7g/+BJDEAQsXLgwqrS0NLexsfE8RVHLFi1atNn7PpVKhdzc3OUvv/zyvg0bNvwmPz8/WeyPt8sHEkLO'
    b'anZaQyCYDUmO47BgwQIsX758VW1t7bc6nU5ISkpSeuYLHMeBYRhkZWWpd+zY8afCwsJklmXBMMwUlw9EX'
    b'jwOhIDL4dHRUQwMDMBms4Hn+YCuJSUKz/NQqVRYsmTJcgDzlixZsnzOnDlu1xfjAMdxoGkaqampsNvtEA'
    b'TBvZ8olzxBEO57whIDxsbGMD4+DrVajaioKERGRoKiKMmdXn9IT09PLi4ufiIxMVEHACzLThGW47gp54I'
    b'hHwz8CiCSEt3P4XDA6XTCYrGApmnQNA2VSuUWwzvyescAl8uF+fPnK59//vm/zp8/f6FoebF98VlSBOWS'
    b'99WXkATwfrhnw+JmiEKhgEKhAEmSEDM6KTEIgkBcXBwRExOTkpCQAJfLNSPkg4EsD/Algncs4Hl+ktv6+'
    b'onjOS0tDTRNT1q4hJN8MCKE5AFSnQx0DQAYhkFqaqpbrJkmH5YPJMJFXqFQTBmTM0E+LB5gt9slXTpU8t'
    b'4E5JKXSnsDkfV+HReUAJ6YLnlf1pNLXhAEmM1msCw7KSZ598/7PEEQ4DgOLMv6VSHQt8JhIS/HG/y5vV6'
    b'vh9FohFqtducN3r8pxCgKJpMJvb29o/hlzzI4AUSEk7yUtfyJwTAMMjMzsXjxYr/zuuf7wbt376K8vLz/'
    b'7NmzlzCxpA5NgHCTl1vHFzkAPjNE774aDAaUl5f3V1RU1HAc9y9MbKr4RMA8QIr4TJP3LEU35zjOnTtIt'
    b'WUwGLB//36R/CVMbKXZQhbAV2dnk7zYD3G1KI537/oURbndvqKi4hTHcV9iYvd4zB/HkFPh6ZL3JurvHI'
    b'BJXuB9XfzG4MCBA/3vvvtujVzysgTwR2I65KVmAl/3iUtmlmUnDQGR/P3793H48GH9A/Ki2wckH1AAzxj'
    b'gS4yZJO/dD899A7EORVEYGRlBVVWV8b333vs4GMvLEsAToQ4Ff+Q92/YniGcMEAUQ5/ljx44Nv/XWWx9Z'
    b'rdaLAJqDIR9QAO/9gHCTlxsERRFEAZRKJUwmE6qrq4cPHjx4xmq11mLi1bglGPIBBfBF8mGQFyHmACaTC'
    b'SdPnhx+++23z4yOjtZi4pWZKVjysgTwFiIU8v7GuVzyIsxmM06fPj188ODBjx5Y/nsAkl+jBoLsPECEry'
    b'Dl7ziQMHLJkyQJi8WCmpqa4YqKCtHtmzAN8oCM9wJKpRIRERGyyAQi6CvwyeokRcFsNqOurm64oqLijMV'
    b'imZbbT2pb6gJN04TNZlNZLBYwDOOeEgNtMsqpF+y1sbEx1NbWDn/wwQdhJQ8AkmZYsWJFVEZGxtZ79+49'
    b'wbIsDa/VlBQJqS0of6QD3UMQBHp7e++YTKYrCIPbe8KfHyoALACwGIAqXA8MEQImPnO7A2AknA3/D+/Oy'
    b'D/Ur3BPAAAAAElFTkSuQmCC'
)

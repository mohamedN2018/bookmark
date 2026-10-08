from .gutenberg import GutenbergProvider
from .oapen import OapenProvider

PROVIDERS = {provider.key: provider for provider in (OapenProvider, GutenbergProvider)}


def get_provider(key):
    try:
        return PROVIDERS[key]()
    except KeyError as exc:
        raise KeyError(f"مزوّد غير معروف: {key}. المتاح: {', '.join(PROVIDERS)}") from exc

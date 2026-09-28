class TxtExtractor:
    def extract(self, data: bytes) -> str:
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError:
            return data.decode("latin-1")
import hashlib


class ReceiptService:

    @staticmethod
    def calculate_sha256(receipt_bytes: bytes) -> str:
        return hashlib.sha256(receipt_bytes).hexdigest()

    @classmethod
    def generate_metadata(cls, receipt_bytes: bytes) -> dict:
        sha256 = cls.calculate_sha256(receipt_bytes)

        return {
            "sha256": sha256,
        }
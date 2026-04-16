import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class EncryptedFileObj:

    def __init__(self, content_iterator, key):
        self.content_iterator = content_iterator
        self.key = key

        self.iv = self._get_initialization_vector()
        self.is_iv_yielded = False

        self.encryptor = self._get_encryptor()

        self.buffer = bytearray()
        self.is_exhausted = False

    @staticmethod
    def _get_initialization_vector():
        return os.urandom(16)

    def _get_encryptor(self):
        return Cipher(algorithms.AES(self.key), modes.CTR(self.iv)).encryptor()

    def read(self, size=-1):
        if not self.is_iv_yielded:
            self.buffer.extend(self.iv)
            self.is_iv_yielded = True

        while (size == -1 or len(self.buffer) < size) and not self.is_exhausted:
            try:
                chunk = next(self.content_iterator)
            except StopIteration:
                self.is_exhausted = True
                self.buffer.extend(self.encryptor.finalize())
            else:
                self.buffer.extend(self.encryptor.update(chunk))

        if size == -1:
            result = bytes(self.buffer)
            self.buffer.clear()
        else:
            result = bytes(self.buffer[:size])
            del self.buffer[:size]
        return result

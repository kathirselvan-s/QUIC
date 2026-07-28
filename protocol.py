import json
import struct
from enum import IntEnum

# ==========================================================
# Protocol Version
# ==========================================================

PROTOCOL_VERSION = 1

# ==========================================================
# Message Types
# ==========================================================

class MessageType(IntEnum):
    FILE_REQUEST = 1
    FILE_DATA = 2
    FILE_COMPLETE = 3
    ERROR = 4
    FILE_LIST = 5
    FILE_LIST_RESPONSE = 6
    ACK = 7
    PING = 8
    PONG = 9


# ==========================================================
# Header Format
# ==========================================================
#
# 1 byte  -> Version
# 1 byte  -> Message Type
# 4 bytes -> Payload Length
#
# Total Header = 6 bytes
#
# ==========================================================

HEADER_FORMAT = "!BBI"

HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


# ==========================================================
# Protocol
# ==========================================================

class Protocol:

    # ------------------------------------------------------
    # Generic Encoder
    # ------------------------------------------------------

    @staticmethod
    def encode(message_type, payload=None):

        if payload is None:
            payload = {}

        payload_bytes = json.dumps(payload).encode("utf-8")

        header = struct.pack(
            HEADER_FORMAT,
            PROTOCOL_VERSION,
            int(message_type),
            len(payload_bytes),
        )

        return header + payload_bytes

    # ------------------------------------------------------
    # Generic Decoder
    # ------------------------------------------------------

    @staticmethod
    def decode(data):

        if len(data) < HEADER_SIZE:
            raise ValueError("Incomplete packet.")

        version, msg_type, payload_size = struct.unpack(
            HEADER_FORMAT,
            data[:HEADER_SIZE],
        )

        if version != PROTOCOL_VERSION:
            raise ValueError(
                f"Unsupported protocol version {version}"
            )

        payload = {}

        if payload_size:

            payload = json.loads(
                data[
                    HEADER_SIZE:
                    HEADER_SIZE + payload_size
                ].decode("utf-8")
            )

        return MessageType(msg_type), payload

    # ------------------------------------------------------
    # File Request
    # ------------------------------------------------------

    @staticmethod
    def file_request(filename, filesize):

        return Protocol.encode(
            MessageType.FILE_REQUEST,
            {
                "filename": filename,
                "filesize": filesize,
            },
        )

    # ------------------------------------------------------
    # File Chunk
    # ------------------------------------------------------

    @staticmethod
    def file_chunk(offset, data):

        payload = struct.pack(
            "!Q",
            offset,
        ) + data

        header = struct.pack(
            HEADER_FORMAT,
            PROTOCOL_VERSION,
            int(MessageType.FILE_DATA),
            len(payload),
        )

        return header + payload

    # ------------------------------------------------------
    # Decode Chunk
    # ------------------------------------------------------

    @staticmethod
    def decode_chunk(data):

        version, msg_type, payload_size = struct.unpack(
            HEADER_FORMAT,
            data[:HEADER_SIZE],
        )

        payload = data[
            HEADER_SIZE:
            HEADER_SIZE + payload_size
        ]

        offset = struct.unpack(
            "!Q",
            payload[:8],
        )[0]

        chunk = payload[8:]

        return offset, chunk

    # ------------------------------------------------------
    # File Complete
    # ------------------------------------------------------

    @staticmethod
    def file_complete():

        return Protocol.encode(
            MessageType.FILE_COMPLETE
        )

    # ------------------------------------------------------
    # ACK
    # ------------------------------------------------------

    @staticmethod
    def ack(message="OK"):

        return Protocol.encode(
            MessageType.ACK,
            {
                "message": message
            },
        )

    # ------------------------------------------------------
    # Error
    # ------------------------------------------------------

    @staticmethod
    def error(message):

        return Protocol.encode(
            MessageType.ERROR,
            {
                "message": message
            },
        )

    # ------------------------------------------------------
    # Ping
    # ------------------------------------------------------

    @staticmethod
    def ping():

        return Protocol.encode(
            MessageType.PING
        )

    # ------------------------------------------------------
    # Pong
    # ------------------------------------------------------

    @staticmethod
    def pong():

        return Protocol.encode(
            MessageType.PONG
        )

    # ------------------------------------------------------
    # File List Request
    # ------------------------------------------------------

    @staticmethod
    def file_list():

        return Protocol.encode(
            MessageType.FILE_LIST
        )

    # ------------------------------------------------------
    # File List Response
    # ------------------------------------------------------

    @staticmethod
    def file_list_response(files):

        return Protocol.encode(
            MessageType.FILE_LIST_RESPONSE,
            {
                "files": files
            },
        )
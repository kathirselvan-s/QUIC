import struct
from enum import IntEnum

class MessageType(IntEnum):
    FILE_REQUEST = 1
    FILE_DATA = 2
    FILE_COMPLETE = 3
    ERROR = 4
    FILE_LIST = 5
    FILE_LIST_RESPONSE = 6

class Protocol:
    @staticmethod
    def encode_file_request(filename):
        """Encode a file request message"""
        filename_bytes = filename.encode('utf-8')
        return struct.pack('!BI', MessageType.FILE_REQUEST, len(filename_bytes)) + filename_bytes
    
    @staticmethod
    def encode_file_data(data, offset=0):
        """Encode file data message"""
        return struct.pack('!BIQ', MessageType.FILE_DATA, len(data), offset) + data
    
    @staticmethod
    def encode_file_complete():
        """Encode file complete message"""
        return struct.pack('!B', MessageType.FILE_COMPLETE)
    
    @staticmethod
    def encode_error(message):
        """Encode error message"""
        msg_bytes = message.encode('utf-8')
        return struct.pack('!BI', MessageType.ERROR, len(msg_bytes)) + msg_bytes
    
    @staticmethod
    def encode_file_list():
        """Encode file list request"""
        return struct.pack('!B', MessageType.FILE_LIST)
    
    @staticmethod
    def encode_file_list_response(files):
        """Encode file list response"""
        files_json = str(files).encode('utf-8')
        return struct.pack('!BI', MessageType.FILE_LIST_RESPONSE, len(files_json)) + files_json
    
    @staticmethod
    def decode_message(data):
        """Decode a message and return (type, payload)"""
        if not data:
            return None, None
        
        msg_type = data[0]
        
        if msg_type == MessageType.FILE_REQUEST:
            _, filename_len = struct.unpack('!BI', data[:5])
            filename = data[5:5+filename_len].decode('utf-8')
            return msg_type, {'filename': filename}
        
        elif msg_type == MessageType.FILE_DATA:
            _, data_len, offset = struct.unpack('!BIQ', data[:13])
            file_data = data[13:13+data_len]
            return msg_type, {'data': file_data, 'offset': offset}
        
        elif msg_type == MessageType.FILE_COMPLETE:
            return msg_type, {}
        
        elif msg_type == MessageType.ERROR:
            _, msg_len = struct.unpack('!BI', data[:5])
            error_msg = data[5:5+msg_len].decode('utf-8')
            return msg_type, {'message': error_msg}
        
        elif msg_type == MessageType.FILE_LIST:
            return msg_type, {}
        
        elif msg_type == MessageType.FILE_LIST_RESPONSE:
            _, list_len = struct.unpack('!BI', data[:5])
            files_data = data[5:5+list_len].decode('utf-8')
            import ast
            files = ast.literal_eval(files_data)
            return msg_type, {'files': files}
        
        return None, None
import linecache
import sys
import traceback


def exception_handler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb = traceback.extract_tb(exc_traceback)
            for frame in reversed(tb):
                if frame.name == func.__name__:
                    filename, line_number, function_name, text = frame
                    break
            else:
                filename, line_number, function_name, text = tb[-1]
            error_line = linecache.getline(filename, line_number).strip()
            error_message = (f"An error occurred in {func.__name__} at line {line_number} of function {function_name}\n"
                             f"Code: {text}\n"
                             f"Error Line Content: {error_line}\n"
                             f"Error: {exc_type.__name__}: {e}")
            print(error_message)
    return wrapper
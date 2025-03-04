import traceback

def handle_error(e):
    tb_lines = traceback.format_exception(type(e), e, e.__traceback__)
    return ''.join(tb_lines)
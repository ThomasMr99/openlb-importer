import re
from functools import cmp_to_key


def sort_intuitive(input_list, reverse=False):
    """
    Sort a list intuitively by using alphabetical order for characters and numerical order for numbers.

    :param input_list: The list to be sorted.
    :param reverse: Optional boolean whether to use reversed string iteration.
    :return: The sorted list.
    """

    def _string_to_list(_input_string):
        pattern = r'\d+(?:[.,]\d+)?|[^\d]'
        result = re.findall(pattern, _input_string)
        return result

    def _string_to_number(_input_string):
        _input_string = _input_string.replace(',', '.')
        try:
            return int(_input_string)
        except ValueError:
            try:
                return float(_input_string)
            except ValueError:
                return None

    def _compare(_x, _y):
        _x = _string_to_list(str(_x))
        _y = _string_to_list(str(_y))

        for i in range(min(len(_x), len(_y))):
            if reverse:
                x_i = _x[len(_x) - i - 1]
                y_i = _y[len(_y) - i - 1]
            else:
                x_i = _x[i]
                y_i = _y[i]
            number_x = _string_to_number(x_i)
            number_y = _string_to_number(y_i)

            if number_x is not None and number_y is not None:
                x_i = number_x
                y_i = number_y

            if x_i < y_i:
                return -1
            elif x_i > y_i:
                return 1

        if len(_x) < len(_y):
            return -1
        elif len(_x) > len(_y):
            return 1
        else:
            return 0

    return sorted(input_list, key=cmp_to_key(_compare))

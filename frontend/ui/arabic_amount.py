"""
Module for converting numbers to Arabic words.
"""

def number_to_arabic_words(number, currency="ليرة سورية"):
    """
    Convert a number to Arabic words.
    
    Args:
        number (float or str): The number to convert
        currency (str): The currency name
        
    Returns:
        str: The number in Arabic words with currency
    """
    try:
        # Convert to float and handle formatting
        if isinstance(number, str):
            # Remove any non-numeric characters except decimal point
            number = ''.join(c for c in number if c.isdigit() or c == '.')
            number = float(number)
        
        # Split into integer and decimal parts
        int_part = int(number)
        decimal_part = int(round((number - int_part) * 100))
        
        # Convert integer part to words
        int_words = _int_to_arabic_words(int_part)
        
        # Format the result
        if decimal_part > 0:
            decimal_words = _int_to_arabic_words(decimal_part)
            return f"{int_words} و {decimal_words} {currency} فقط لا غير"
        else:
            return f"{int_words} {currency} فقط لا غير"
    except Exception as e:
        print(f"Error converting number to Arabic words: {e}")
        return f"{number} {currency} فقط لا غير"

def _int_to_arabic_words(number):
    """
    Convert an integer to Arabic words.
    
    Args:
        number (int): The integer to convert
        
    Returns:
        str: The integer in Arabic words
    """
    if number == 0:
        return "صفر"
    
    # Arabic words for numbers
    ones = ["", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة"]
    tens = ["", "عشرة", "عشرون", "ثلاثون", "أربعون", "خمسون", "ستون", "سبعون", "ثمانون", "تسعون"]
    teens = ["عشرة", "أحد عشر", "اثنا عشر", "ثلاثة عشر", "أربعة عشر", "خمسة عشر", 
             "ستة عشر", "سبعة عشر", "ثمانية عشر", "تسعة عشر"]
    hundreds = ["", "مائة", "مائتان", "ثلاثمائة", "أربعمائة", "خمسمائة", "ستمائة", "سبعمائة", "ثمانمائة", "تسعمائة"]
    thousands = ["", "ألف", "ألفان", "آلاف", "آلاف", "آلاف", "آلاف", "آلاف", "آلاف", "آلاف"]
    millions = ["", "مليون", "مليونان", "ملايين", "ملايين", "ملايين", "ملايين", "ملايين", "ملايين", "ملايين"]
    
    if 1 <= number <= 9:
        return ones[number]
    elif 10 <= number <= 19:
        return teens[number - 10]
    elif 20 <= number <= 99:
        ten_digit = number // 10
        one_digit = number % 10
        if one_digit == 0:
            return tens[ten_digit]
        else:
            return f"{ones[one_digit]} و {tens[ten_digit]}"
    elif 100 <= number <= 999:
        hundred_digit = number // 100
        remainder = number % 100
        if remainder == 0:
            return hundreds[hundred_digit]
        else:
            return f"{hundreds[hundred_digit]} و {_int_to_arabic_words(remainder)}"
    elif 1000 <= number <= 999999:
        thousand_part = number // 1000
        remainder = number % 1000
        
        if thousand_part == 1:
            thousand_word = "ألف"
        elif thousand_part == 2:
            thousand_word = "ألفان"
        elif 3 <= thousand_part <= 10:
            thousand_word = f"{_int_to_arabic_words(thousand_part)} آلاف"
        else:
            thousand_word = f"{_int_to_arabic_words(thousand_part)} ألف"
            
        if remainder == 0:
            return thousand_word
        else:
            return f"{thousand_word} و {_int_to_arabic_words(remainder)}"
    elif 1000000 <= number <= 999999999:
        million_part = number // 1000000
        remainder = number % 1000000
        
        if million_part == 1:
            million_word = "مليون"
        elif million_part == 2:
            million_word = "مليونان"
        elif 3 <= million_part <= 10:
            million_word = f"{_int_to_arabic_words(million_part)} ملايين"
        else:
            million_word = f"{_int_to_arabic_words(million_part)} مليون"
            
        if remainder == 0:
            return million_word
        else:
            return f"{million_word} و {_int_to_arabic_words(remainder)}"
    else:
        return str(number)  # Fallback for very large numbers

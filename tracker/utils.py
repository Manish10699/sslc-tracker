from datetime import date

def get_current_academic_year():
    today = date.today()
    if today.month >= 5:  # May onwards = new academic year starts
        return f"{today.year}-{str(today.year + 1)[-2:]}"
    else:  # Jan-April = still last year's academic year
        return f"{today.year - 1}-{str(today.year)[-2:]}"
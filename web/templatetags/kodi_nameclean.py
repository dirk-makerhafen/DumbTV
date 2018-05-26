from django import template
import re

register = template.Library()

@register.filter
def clean(string):
    return re.sub("[\[].*?[\]]", "", string)
    
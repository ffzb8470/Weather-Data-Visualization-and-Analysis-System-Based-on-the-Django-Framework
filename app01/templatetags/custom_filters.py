# -*- coding: utf-8 -*-
from django import template

register = template.Library()  # Library()：创建 Django 模板标签库注册器

@register.filter  # @register.filter：将该函数注册为模板过滤器，可在模板中用 {{ dict|get_item:key }} 调用
def get_item(dictionary, key):
    """字典取值过滤器：{{ dict|get_item:key }}"""
    if dictionary is None:  # 防御性判断：模板可能传 None
        return ''
    return dictionary.get(key, '')  # .get()：安全取字典值，key 不存在时返回空字符串

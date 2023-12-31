# -*- coding: utf-8 -*-
'''
Created on 2020年8月1日

@author: Xiaoyong
'''
import hashlib
import random
import string
import base64
import io
import platform
_system = platform.system().lower()
if _system == 'windows':
    import win32com.client
    import win32gui
    import win32api
    import win32con
import socket
import time
import datetime
import json
import uuid
import os
import shutil
import sys
import re
import WuLaiBase
import base64
import fitz
import ImageHelper
import requests
if _system == 'windows':
    import Excel
if _system == 'linux':
    import WPSEXCEL as Excel
import numpy as np
import copy

try:
    import UiBot
except Exception as e:
    class Temp():
        def GetString(self, strPath):
            return strPath
        def Log(self, file_name, line_num, level, msg):
            return True
    UiBot = Temp()
#https://mage.uibot.com.cn/
#TODO:测试环境，上线前需替换线上环境的URL
url_route_dict = {'default_base_url': 'https://mage.uibot.com.cn/',  #默认公网url
                  'text': 'v1/mage/ocr/general',  #通用文本
                  'table': 'v1/mage/ocr/table',  #表格
                  'card': 'v1/mage/ocr/license',  # 卡证
                  'bill': 'v1/mage/ocr/bills',  # 多票据
                  'stamp': 'v1/mage/ocr/stamp',  # 印章
                  'verify_code': 'v1/document/ocr/verification',  # 验证码
                  'addr_std': 'v1/mage/nlp/geoextract',  # 地址标准化
                  'text_classify': 'v1/document/classify',  # 文本分类
                  'text_extract': 'v1/document/extract',  # 文本信息提取
                  'ocr_template': 'v1/document/ocr/template',  # 自定义模板识别
                  'text_extract_query_version_list': 'v1/app/extractor/version/list',  # 查询文本信息提取的版本列表
                  'text_extract_query_template_list': 'v1/app/extractor/template/list',  # 查询文本信息提取的模板列表
                  'ocr_template_query_template_list': 'v1/app/ocrtemplate/template/list',  # 查询自定义模板的模板列表
                  'listbykey': 'v1/app/listbykey',  #查询识别器信息
                  'docextract_create':'v1/mage/nlp/docextract/create',#文档抽取创建任务
                  'docextract_query':'v1/mage/nlp/docextract/query',#文档抽取获取结果
                  'idp_extractor_create':'v1/mage/idp/extractor/create',#多页抽取模型-提交任务
                  'idp_extractor_query':'v1/mage/idp/extractor/query',#多页抽取模型-获取结果
                  'field_list':'v1/app/field/list',#获取字段列表。目前支持信息抽取、文档抽取、单页抽取模型、多页抽取模型
                  'idp_extractor_single_create':'v1/idp/extractor/single/create',#单据自训练抽取模型-提交任务
                  'idp_extractor_single_query':'v1/idp/extractor/single/query',#单据自训练抽取模型-获取结果
                  'idp_doc_classification_create':'v1/mage/self_train/doc/create_classification_task',#文档分类模型-提交任务
                  'idp_doc_classification_query':'v1/mage/self_train/doc/query_classification_task'#文档分类模型-获取结果
                  }

#网络请求相关功能实现
class MageClient():
    def __init__(self, _base_url):
        self.base_url = _base_url

    def _get_language(self):
        lang_type = "zh-CN" #"zh-CN"简体中文; "en"通用英文
        if hasattr(UiBot, 'GetRuntimeInfo'):
            language_type = UiBot.GetRuntimeInfo("Language")
            if _system == 'windows':
                win32api.OutputDebugString("GetRuntimeInfo return Language type:{0}".format(language_type))
            if language_type.strip().lower() == "zh-cn":
                lang_type = "zh-CN"
            elif language_type.strip().lower() == "en-us":
                lang_type = "en"
            else:
                lang_type = language_type.strip()
        if _system == 'windows':
            win32api.OutputDebugString("_get_language---->lang_type:{0}".format(lang_type))
        return lang_type

    def _get_product_version(self):
        version = ""
        if hasattr(UiBot, 'GetRuntimeInfo'):
            version = UiBot.GetRuntimeInfo("ProductVersion")
            print("version:{0}".format(version))
        return version

    # 生成请求header信息
    def generate_header(self, api_auth_pubkey, app_auth_secretkey):
        api_auth_timestamp = str(int(time.time()))
        api_auth_nounce = "".join(random.sample(string.ascii_letters + string.digits, 10))  # 随机生成长度为10的字符串
        HeaderDict = dict()
        HeaderDict['content-type'] = 'application/json'
        HeaderDict['Accept-Language'] = self._get_language()
        HeaderDict['Api-Auth-client-version'] = self._get_product_version()
        HeaderDict["Api-Auth-nonce"] = api_auth_nounce
        HeaderDict["Api-Auth-pubkey"] = api_auth_pubkey
        HeaderDict["Api-Auth-timestamp"] = api_auth_timestamp
        token_name = hashlib.sha1()
        token_key = api_auth_nounce + api_auth_timestamp + app_auth_secretkey
        token_name.update(token_key.encode("utf-8"))
        HeaderDict["Api-Auth-sign"] = token_name.hexdigest()
        return HeaderDict

    # 生成OCR能力的body信息，对于通用文字识别和表格文字识别body中是img_base64数组，而其余的是img_base64字符串
    def generate_body(self, filename, with_struct_info=None, base64_type="str", with_char_info=False):
        if not os.path.exists(filename):
            raise Exception(UiBot.GetString("Mage/FileNotExist"))
        with open(filename, "rb") as img_file:
            img = img_file.read()
            byte_size = io.BytesIO(img).read()
            #图片文件的大小限制为10M
            img_base64 = ''
            if len(byte_size) > 20 * 1024 * 1024:
                raise Exception(UiBot.GetString("Mage/ImageSizeTooBig"))
            else:
                img_base64 = base64.b64encode(img).decode("utf-8")

        body_dict = dict()
        if base64_type == "str":
            body_dict['img_base64'] = img_base64
        else:
            body_dict['img_base64'] = []
            body_dict['img_base64'].append(img_base64)

        if with_struct_info is not None:
            body_dict["with_struct_info"] = with_struct_info
        
        body_dict['with_char_info'] = with_char_info
        return body_dict

    def generate_body_for_template(self, filename):
        body_dict = self.generate_body(filename, with_struct_info = False)
        body_dict["with_raw_info"] = True#www False
        return body_dict

    def generate_body_for_text(self, text):
        body_dict = dict()
        body_dict["text"] = text
        return body_dict

    def generate_body_for_text_extract_version_list(self):
        body_dict = dict()
        filter_dict = dict()
        filter_dict["status"] = 4   #版本状态：1训练中 2评测中 3未发布 4已发布
        body_dict["filter"] = filter_dict
        body_dict["page_num"] = 1
        body_dict["page_size"] = 200
        return body_dict

    def generate_body_for_text_extract_template_list(self, version_hash, page_id, page_size):
        body_dict = dict()
        body_dict["version_hash"] = version_hash
        body_dict["page_num"] = page_id
        body_dict["page_size"] = page_size
        return body_dict

    def generate_body_for_ocr_template_list(self, page_id, page_size):
        body_dict = dict()
        filter_dict = dict()
        filter_dict["status"] = 1   #模板状态： 0未生效 1生效
        body_dict["filter"] = filter_dict
        body_dict["page_num"] = page_id
        body_dict["page_size"] = page_size
        return body_dict

    def generate_body_for_doc(self, text):
        body_dict = dict()
        body_dict["doc"] = text
        return body_dict

    def generate_body_for_query_recognizer(self, pubkey, secret):
        body_dict = dict()
        keys_list = list()
        keys = dict()
        keys["pub_key"] = pubkey
        keys["secret_key"] = secret
        keys_list.append(keys)
        body_dict['keys'] = keys_list
        return body_dict

    #time_out参数为毫秒为单位
    def do_request(self, url_route, header, body, time_out):
        url = ''
        if self.base_url[-1] == '/':
            url = self.base_url + url_route
        else:
            url = self.base_url + '/' + url_route
        mage_client = WuLaiBase.WuLaiBase('', '')
        mage_client.setConnectionTimeoutInMillis(time_out)
        mage_client.setSocketTimeoutInMillis(time_out)
        res_data = mage_client.post(url, body, header)
        if 'error' in res_data:
            raise Exception(UiBot.GetString("Mage/HttpErr") + r"，" + '{0}'.format(res_data.get('error')))
        return res_data

#--------------add by www-------------
    #add by www 单页抽取模型有with_ocr_detail参数，其他没有
    def generate_file_body(self, filename, with_ocr_detail=None):
        with open(filename, "rb") as img_file:
            img = img_file.read()
            byte_size = io.BytesIO(img).read()
            #图片文件的大小限制为10M
            file_base64 = ''
            if len(byte_size) > 20 * 1024 * 1024:
                raise Exception(UiBot.GetString("Mage/ImageSizeTooBig"))
            else:
                file_base64 = base64.b64encode(img).decode("utf-8")

        body_dict = dict()
        body_dict['file_base64'] = file_base64

        if with_ocr_detail is not None:
            body_dict["with_ocr_detail"] = with_ocr_detail
        
        return body_dict

    def show_tip(self,wait_start):
        from urllib.parse import quote
        tip_icon = '0'
        tip_title = UiBot.GetString("Mage/TipTitle")
        text_tpl = UiBot.GetString("Mage/TipContentTpl")
        
        now = datetime.datetime.now()
        seconds = (now - wait_start).seconds
        tip_text = text_tpl % (seconds // 60 // 60 // 24, seconds // 60 // 60 % 60, seconds // 60 % 60, seconds % 60)
        UiBot.ExecuteStatement(
            "BasicLib.Notify(BasicLib.UrlDecode('" + quote(tip_text) + "'),'" + tip_title + "'," + tip_icon + ")")

    def generate_body_for_field_list(self):
        body_dict = dict()
        body_dict["page_num"] = 1
        body_dict["page_size"] = 200
        return body_dict

############################################################
#日志记录
############################################################
#全局成员
global_static_map_pubkey_recognizer = dict()
class Recognizer:
    def __init__(self):
        self.ai_function = 0
        self.engine_name = ''
        self.app_name = ''
        self.left_quota = 0

class LogRecord:
    def __init__(self):
        self.log_url = r'http://statics.uibot.com.cn/api/log/mage'
        self.product_id_dict = {'c': 'creator', 'C': 'creator_enterprise', 'W': 'worker', 's': 'store'}

    def _get_running_time_info(self):
        #TODO:反调UiBot，获取bot_source， version， machine_code， user_name等信息
        if hasattr(UiBot, 'GetRuntimeInfo'):
            machine_code = UiBot.GetRuntimeInfo("MachineCode")
            version = UiBot.GetRuntimeInfo("ProductVersion")
            product_id_key = UiBot.GetRuntimeInfo("ProductId")[0]
            user_name = UiBot.GetRuntimeInfo("UserName")
            print("product_id_key:{0}; version:{1}; machine_code:{2}; user_name:{3}".format(product_id_key, version, machine_code, user_name))
        else:
            raise Exception(UiBot.GetString("Mage/LogRecord/GetRuntimeInfoErr"))

        bot_source = self.product_id_dict.get(product_id_key)
        return bot_source, version, machine_code, user_name

    def _generate_sign(self, bot_source, version, machine_code):
        md5 = hashlib.md5()
        sign_key = r'ce23986bc5rt4dc09dg67jkh6ab14912'
        content = bot_source + r',' + version + r',' + machine_code + r',' + sign_key
        md5.update(content.encode('utf-8'))
        return md5.hexdigest()

    def _query_recognizer_from_mage_api(self, pubkey, secret):
        mage_client = MageClient(url_route_dict['default_base_url'])
        header_dict = mage_client.generate_header(pubkey, secret)
        body_dict = mage_client.generate_body_for_query_recognizer(pubkey, secret)
        ret_json = mage_client.do_request(url_route_dict['listbykey'], header_dict, body_dict, 3000)
        #ret_json = requests.post(self.mage_app_listbykey_base_url, headers=header_dict, json=body_dict, timeout=(3, 3)).json()
        if "code" not in ret_json or ret_json.get("code") != 0 or "data" not in ret_json:
            # 这是日志埋点功能，抛出的异常不会往界面显示，所以未做国际化处理
            raise Exception(UiBot.GetString("Mage/LogRecord/QueryRecognizerErr"))

        recognizer_info_arr = ret_json.get("data")
        if len(recognizer_info_arr) <= 0:
            # 这是日志埋点功能，抛出的异常不会往界面显示，所以未做国际化处理
            raise Exception(UiBot.GetString("Mage/LogRecord/QueryRecognizerErr"))

        recognizer = Recognizer()
        recognizer.ai_function = recognizer_info_arr[0].get("ai_function")
        recognizer.engine_name = recognizer_info_arr[0].get("engine_name")
        recognizer.app_name = recognizer_info_arr[0].get("app_name")
        recognizer.left_quota = recognizer_info_arr[0].get("left_quota")
        return recognizer

    # 通过pubkey+secret从mage反查对应的识别器的信息，缓存
    def _get_recognizer_info(self, pubkey, secret):
        global global_static_map_pubkey_recognizer
        if pubkey in global_static_map_pubkey_recognizer:
            print("get recognizer info from cache..................")
            return global_static_map_pubkey_recognizer.get(pubkey)
        # 调用API获取识别器信息
        recognizer = self._query_recognizer_from_mage_api(pubkey, secret)
        global_static_map_pubkey_recognizer[pubkey] = recognizer
        return recognizer

    def is_need_upload_log(self, mage_server, bot_source):
        if mage_server[-1] != '/':
            mage_server = mage_server + '/'
        # 仅公有云版本的Creator社区版才会记录调用日志
        return (mage_server == url_route_dict['default_base_url']) and (bot_source == r'creator')

    def upload_log(self, pubkey, secret, success_state, command, mage_server):
        try:
            # 获取用户及产品信息
            bot_source, version, machine_code, user_name = self._get_running_time_info()
            if (not self.is_need_upload_log(mage_server, bot_source)):
                print("do not need upload log!!!")
                return
            is_login = 0 if len(user_name) == 0 else 1
            sign_key = self._generate_sign(bot_source, version, machine_code)
            # 初始化识别器信息
            recognizer_info = self._get_recognizer_info(pubkey, secret)
            ai_function = recognizer_info.ai_function
            engine_name = recognizer_info.engine_name
            app_name = recognizer_info.app_name

            head_dict = dict()
            head_dict['content-type'] = 'application/json'
            body_dict = dict()
            body_dict['Sign'] = sign_key
            body_dict['Source'] = bot_source
            body_dict['Version'] = version
            body_dict['MAC'] = machine_code
            body_dict['IsLogin'] = is_login
            body_dict['IsSuccess'] = success_state
            body_dict['Command'] = command
            body_dict['Server'] = mage_server
            body_dict['Module'] = str(ai_function)
            body_dict['CreateBy'] = user_name
            body_dict['Recognizer'] = app_name
            body_dict['Ability'] = engine_name
            body_data = json.dumps(body_dict)
            ret = requests.post(self.log_url, headers=head_dict, json=body_dict, timeout=(3, 3))
            print("upload log:{0}".format(body_data))
            return ret.json()
        except Exception as e:
            err_msg = str(e)
            print("LogRecord->upload_log Exception:{0}".format(err_msg))
            return err_msg

#命令参数校验等功能实现
class ParamUtil:
    def __init__(self):
        return

    def get_file_name_param(self, file_name):
        if not isinstance(file_name, str):
            raise Exception(UiBot.GetString("Mage/ImageFilePathNameTypeErr"))
        if not (file_name and os.path.isfile(file_name)):
            raise Exception(UiBot.GetString("Mage/NotImageFile"))
        # 校验文件后缀
        # 取消文件后缀的校验
        # img_suffix_set = {'.png', '.jpeg', '.jpg', '.bmp', '.tiff', '.tif'}
        # suffix = os.path.splitext(file_name)[-1]
        # if suffix not in img_suffix_set:
        #     raise Exception(UiBot.GetString("Mage/NotImageFile"))
        return file_name

    def get_text_file_name_param(self, file_name):
        if not isinstance(file_name, str):
            raise Exception(UiBot.GetString("Mage/TextFilePathNameTypeErr"))
        if not (file_name and os.path.isfile(file_name)):
            raise Exception(UiBot.GetString("Mage/NotTextFile"))
        return file_name

    def get_pdf_file_name_param(self, file_name):
        if not isinstance(file_name, str):
            raise Exception(UiBot.GetString("Mage/PDFFilePathNameTypeErr"))
        if not (file_name and os.path.isfile(file_name)):
            raise Exception(UiBot.GetString("Mage/NotPDFFile"))
        return file_name

    def get_mage_access_param(self, mage_cfg_dict):
        if not isinstance(mage_cfg_dict, dict):
            raise Exception(UiBot.GetString("Mage/PubSecretkeyNotValid"))
        if not mage_cfg_dict:
            raise Exception(UiBot.GetString("Mage/MageCfgIsEmpty"))
        if ('Pubkey' not in mage_cfg_dict) or ('Secret' not in mage_cfg_dict):
            raise Exception(UiBot.GetString("Mage/PubSecretkeyNotValid"))

        pubkey = mage_cfg_dict.get('Pubkey', '')
        secret = mage_cfg_dict.get('Secret', '')
        if len(pubkey.strip()) == 0:
            raise Exception(UiBot.GetString("Mage/PubkeyIsEmpty"))
        if len(secret.strip()) == 0:
            raise Exception(UiBot.GetString("Mage/SecretIsEmpty"))
        if not isinstance(pubkey, str):
            raise Exception(UiBot.GetString("Mage/PubkeyTypeErr"))
        if not isinstance(secret, str):
            raise Exception(UiBot.GetString("Mage/SecretTypeErr"))

        default_base_url = url_route_dict['default_base_url']
        base_url = mage_cfg_dict.get('Url', "")
        if not isinstance(base_url, str):
            raise Exception(UiBot.GetString("Mage/URLTypeErr"))
        if len(base_url.strip()) == 0:
            base_url = default_base_url
        return pubkey, secret, base_url

    def get_mage_access_param_ex(self, mage_cfg_dict):
        if not isinstance(mage_cfg_dict, dict):
            raise Exception(UiBot.GetString("Mage/PubSecretkeyNotValid"))
        if not mage_cfg_dict:
            raise Exception(UiBot.GetString("Mage/MageCfgIsEmpty"))
        if ('Pubkey' not in mage_cfg_dict) or ('Secret' not in mage_cfg_dict):
            raise Exception(UiBot.GetString("Mage/PubSecretkeyNotValid"))

        pubkey = mage_cfg_dict.get('Pubkey', '')
        secret = mage_cfg_dict.get('Secret', '')
        if len(pubkey.strip()) == 0:
            raise Exception(UiBot.GetString("Mage/PubkeyIsEmpty"))
        if len(secret.strip()) == 0:
            raise Exception(UiBot.GetString("Mage/SecretIsEmpty"))
        if not isinstance(pubkey, str):
            raise Exception(UiBot.GetString("Mage/PubkeyTypeErr"))
        if not isinstance(secret, str):
            raise Exception(UiBot.GetString("Mage/SecretTypeErr"))

        default_base_url = url_route_dict['default_base_url']
        base_url = mage_cfg_dict.get('Url', "")
        if not isinstance(base_url, str):
            raise Exception(UiBot.GetString("Mage/URLTypeErr"))
        if len(base_url.strip()) == 0:
            base_url = default_base_url
        
        ai_name = mage_cfg_dict.get('Name', "")
        if not isinstance(ai_name, str):
            raise Exception(UiBot.GetString("Mage/AiNameTypeErr"))
        if len(ai_name.strip()) == 0:
            raise Exception(UiBot.GetString("Mage/AiNameIsEmpty"))
        return pubkey, secret, base_url,ai_name        

    def get_update_time_param(self, _update_time):
        if not isinstance(_update_time, str):
            raise Exception(UiBot.GetString("Mage/UpdateTimeTypeErr"))
        return _update_time

    def get_ai_function(self, mage_cfg_dict):
        default_ai_function = 'ocr_text'
        if not isinstance(mage_cfg_dict, dict):
            raise Exception(UiBot.GetString("Mage/PubSecretkeyNotValid"))
        ai_function = mage_cfg_dict.get('AIFunction', "")
        if not isinstance(ai_function, str):
            raise Exception(UiBot.GetString("Mage/AiFunctionTypeErr"))
        if len(ai_function.strip()) == 0:
            ai_function = default_ai_function
        return ai_function

    def get_password(self, _password):
        if _password is None:
            return ""
        if not isinstance(_password, str):
            raise Exception(UiBot.GetString("Mage/PasswordTypeErr"))
        return _password

    def get_pdf_all_page_status(self, _is_all_page):
        if isinstance(_is_all_page, int):
            b_is_all_page = bool(_is_all_page)
        else:
            raise Exception(UiBot.GetString("Mage/PDFAllPageStateTypeErr"))
        return b_is_all_page

    def get_is_std_value(self, _is_std_value):
        if isinstance(_is_std_value, int):
            b_is_std_value = bool(_is_std_value)
        else:
            raise Exception(UiBot.GetString("Mage/IsStdValueTypeErr"))
        return b_is_std_value

    def get_pdf_page_cfg(self, _page_cfg, page_count):
        page_list = list()
        if isinstance(_page_cfg, list):
            # 数组.[1, [4, 6], [9, 13]]  第1页，第4到第6页， 第9到第13页
            for page_cfg_item in _page_cfg:
                if isinstance(page_cfg_item, int):  # 二维数组中的元素为int整数
                    if page_cfg_item < 1:
                        raise Exception(UiBot.GetString("Mage/PDFPageCfgSubTypeErr"))
                    if page_cfg_item > page_count:
                        raise Exception(UiBot.GetString("Mage/PDFPageOutOfRange"))
                    page_list.append(page_cfg_item)
                elif isinstance(page_cfg_item, list):  # 二维数组中的元素为list
                    if len(page_cfg_item) != 2:
                        raise Exception(UiBot.GetString("Mage/PDFPageCfgSubTypeErr"))
                    start_pg, end_pg = page_cfg_item[0], page_cfg_item[1]
                    if not isinstance(start_pg, int) or not isinstance(end_pg, int):
                        raise Exception(UiBot.GetString("Mage/PDFPageCfgNotValid"))
                    if start_pg < 1 or end_pg < 1:
                        raise Exception(UiBot.GetString("Mage/PDFPageCfgNotValid"))
                    if start_pg > end_pg:
                        raise Exception(UiBot.GetString("Mage/PDFPageCfgNotValid"))
                    if start_pg > page_count or end_pg > page_count:
                        raise Exception(UiBot.GetString("Mage/PDFPageOutOfRange"))
                    for pg in range(start_pg, end_pg + 1):
                        page_list.append(pg)
                else:  # 二维数组中的元素类型错误
                    raise Exception(UiBot.GetString("Mage/PDFPageCfgSubTypeErr"))
        elif isinstance(_page_cfg, int):
            if _page_cfg < 1:
                raise Exception(UiBot.GetString("Mage/PDFPageCfgNotValid"))
            if _page_cfg > page_count:
                raise Exception(UiBot.GetString("Mage/PDFPageOutOfRange"))
            page_list.append(_page_cfg)
        else:
            raise Exception(UiBot.GetString("Mage/PDFPageCfgTypeErr"))

        # 去重
        news_page_list = list()
        for page in page_list:
            if page not in news_page_list:
                news_page_list.append(page)
        news_page_list.sort()
        return news_page_list

    def get_struct_status(self, with_struct_info):
        if isinstance(with_struct_info, int):
            b_with_struct_info = bool(with_struct_info)
        else:
            raise Exception(UiBot.GetString("Mage/StructStateTypeErr"))
        return b_with_struct_info

    def get_option_param(self, option):
        if not isinstance(option, dict):
            raise Exception(UiBot.GetString("Mage/OptionNotValid"))
        return option

    def get_delay_param(self, option):
        delay_before = option.get('iDelayBefore', 0)
        if isinstance(delay_before, int):
            if (delay_before < 0):
                raise Exception(UiBot.GetString("Mage/DelayTimeTypeErr"))
        else:
            raise Exception(UiBot.GetString("Mage/DelayTimeTypeErr"))
        delay_after = option.get('iDelayAfter', 0)
        if isinstance(delay_after, int):
            if (delay_after < 0):
                raise Exception(UiBot.GetString("Mage/DelayTimeTypeErr"))
        else:
            raise Exception(UiBot.GetString("Mage/DelayTimeTypeErr"))
        return delay_before, delay_after

    def get_continue_on_err_param(self, option):
        continue_on_err = option.get('bContinueOnError', False)
        if isinstance(continue_on_err, int):
            continue_on_err = bool(continue_on_err)
        else:
            raise Exception(UiBot.GetString("Mage/ContinueOnErrTypeErr"))
        return continue_on_err

    def get_active_window_param(self, option):
        active_window = option.get('bSetForeground', True)
        if isinstance(active_window, int):
            active_window = bool(active_window)
        else:
            raise Exception(UiBot.GetString("Mage/ActiveWindowTypeErr"))
        return active_window

    def get_time_out_param(self, time_out):
        if isinstance(time_out, int):
            if (time_out <= 0):
                raise Exception(UiBot.GetString("Mage/TimeOutTypeErr"))
        else:
            raise Exception(UiBot.GetString("Mage/TimeOutTypeErr"))
        return time_out

    def get_template_name(self, _template_name):
        if not isinstance(_template_name, str):
            raise Exception(UiBot.GetString("Mage/TemplateNameTypeErr"))
        return _template_name

    def get_interval_time_param(self, interval_time):
        if isinstance(interval_time, int):
            if (interval_time < 0):
                raise Exception(UiBot.GetString("Mage/IntervalTimeTypeErr"))
        else:
            raise Exception(UiBot.GetString("Mage/IntervalTimeTypeErr"))
        return interval_time

    def get_element_param(self, element):
        if not isinstance(element, dict) and not isinstance(element,UiBot.RawObject):
            raise Exception(UiBot.GetString("Mage/ElementNotValid"))
        return element

    def get_rect_param(self, rect):
        if not isinstance(rect, dict):
            raise Exception(UiBot.GetString("Mage/RectTypeErr"))
        if ('x' not in rect) or ('y' not in rect) or ('width' not in rect) or ('height' not in rect):
            raise Exception(UiBot.GetString("Mage/RectTypeErr"))
        x = rect.get('x')
        y = rect.get('y')
        width = rect.get('width')
        height = rect.get('height')
        if not isinstance(x, int) or x < 0:
            raise Exception(UiBot.GetString("Mage/RegionNotValid"))
        if not isinstance(y, int) or y < 0:
            raise Exception(UiBot.GetString("Mage/RegionNotValid"))
        if not isinstance(width, int) or width < 0:
            raise Exception(UiBot.GetString("Mage/RegionNotValid"))
        if not isinstance(height, int) or height < 0:
            raise Exception(UiBot.GetString("Mage/RegionNotValid"))
        return x, y, width, height

    def get_address(self, _address):
        if not isinstance(_address, str):
            raise Exception(UiBot.GetString("Mage/AddressTypeErr"))
        if len(_address) == 0:
            raise Exception(UiBot.GetString("Mage/AddressNotValid"))
        return _address

    def get_classify_text(self, _text):
        if not isinstance(_text, str):
            raise Exception(UiBot.GetString("Mage/TextClassifyTypeErr"))
        if len(_text) == 0:
            raise Exception(UiBot.GetString("Mage/TextClassifyNotValid"))
        return _text

    def get_extract_text(self, _text):
        if not isinstance(_text, str):
            raise Exception(UiBot.GetString("Mage/TextExtractTypeErr"))
        if len(_text) == 0:
            raise Exception(UiBot.GetString("Mage/TextExtractNotValid"))
        if len(_text) > 30000:
            raise Exception(UiBot.GetString("Mage/TextSizeTooLong"))
        return _text

    def get_filter_text_status(self, _filter_text_status):
        if isinstance(_filter_text_status, int):
            b_filter_text_status = bool(_filter_text_status)
        else:
            raise Exception(UiBot.GetString("Mage/FilterTextTypeErr"))
        return b_filter_text_status

    def get_enter_status(self, _enter_status):
        if isinstance(_enter_status, int):
            b_enter_status = bool(_enter_status)
        else:
            raise Exception(UiBot.GetString("Mage/EnterTypeErr"))
        return b_enter_status

    def get_score_thrd_param(self, _score_thrd):
        if isinstance(_score_thrd, int):
            _score_thrd = float(_score_thrd)
        if isinstance(_score_thrd, float):
            if (_score_thrd < 0 or _score_thrd > 1.0):
                raise Exception(UiBot.GetString("Mage/ScoreThrdNotValid"))
        else:
            raise Exception(UiBot.GetString("Mage/ScoreThrdNotValid"))
        return _score_thrd

    def get_top_n_param(self, _top_n):
        if isinstance(_top_n, int):
            if _top_n <= 0:
                raise Exception(UiBot.GetString("Mage/TopNNotValid"))
        else:
            raise Exception(UiBot.GetString("Mage/TopNNotValid"))
        return _top_n

    def get_table_id_param(self, _table_id):
        if isinstance(_table_id, int):
            if _table_id < 0:
                raise Exception(UiBot.GetString("Mage/TableIdNotValid"))
        else:
            raise Exception(UiBot.GetString("Mage/TableIdNotValid"))
        return _table_id

    def get_index_param(self, _index):
        if isinstance(_index, int):
            if _index < 0:
                raise Exception(UiBot.GetString("Mage/IndexNotValid"))
        else:
            raise Exception(UiBot.GetString("Mage/IndexNotValid"))
        return _index

    def get_table_obj_param(self, _table_obj):
        if isinstance(_table_obj, list):
            y = np.array(_table_obj)
            if y.ndim != 2:  # 不是2维数组，数据不合理
                raise Exception(UiBot.GetString("Mage/TableObjNotValid"))
        else:
            raise Exception(UiBot.GetString("Mage/TableObjNotValid"))
        return _table_obj

    def get_row_and_col_param(self, row_or_col):
        if isinstance(row_or_col, int):
            if row_or_col <= 0:
                raise Exception(UiBot.GetString("Mage/RowAndColumnAreOneBased"))
        else:
            raise Exception(UiBot.GetString("Mage/RowAndColumnAreOneBased"))
        return row_or_col

    def get_table_range_param(self, _start_row, _start_col, _end_row, _end_col):
        start_row = self.get_row_and_col_param(_start_row)
        start_col = self.get_row_and_col_param(_start_col)
        end_row = self.get_row_and_col_param(_end_row)
        end_col = self.get_row_and_col_param(_end_col)
        if start_row > end_row or start_col > end_col:
            raise Exception(UiBot.GetString("Mage/TableRangeNotValid"))
        return start_row, start_col, end_row, end_col



#---------- add by caichengqiang -------------
    def get_text_param(self, text):
        if not isinstance(text, str):
            raise Exception(UiBot.GetString("Mage/TextTypeErr"))
        if text == "":
            raise Exception(UiBot.GetString("Mage/TextToSearchEmpty"))
        return text

    def get_rule_param(self, rule):
        if not isinstance(rule, str):
            raise Exception(UiBot.GetString("Mage/RuleTypeErr"))
        if rule not in ('equal', 'regex', 'instr'):
            raise Exception(UiBot.GetString("Mage/RuleNotFound"))
        return rule

    def get_occurrence_param(self, occurrence):
        if not isinstance(occurrence, int):
            raise Exception(UiBot.GetString("Mage/OccurrenceTypeErr"))
        if occurrence < 1:
            raise Exception(UiBot.GetString("Mage/OccurrenceRangeErr"))
        return occurrence

    def get_button_param(self, button):
        if not isinstance(button, str):
            raise Exception(UiBot.GetString("Mage/ButtonTypeErr"))
        if button not in ('left', 'middle', 'right'):
            raise Exception(UiBot.GetString("Mage/ButtonNotFound"))
        return button

    def get_click_type_param(self, click_type):
        if not isinstance(click_type, str):
            raise Exception(UiBot.GetString("Mage/ClickTypeErr"))
        if click_type not in ('click', 'dbclick', 'down', 'up'):
            raise Exception(UiBot.GetString("Mage/ClickTypeErr"))
        return click_type

    def get_cursor_postion_param(self, option):
        cursor_position = option.get('sCursorPosition', None)
        if cursor_position is None or not isinstance(cursor_position, str):
            raise Exception(UiBot.GetString("Mage/CursorPositionTypeErr"))
        if cursor_position not in ['Center', 'TopLeft', 'TopRight', 'BottomLeft', 'BottomRight']:
            raise Exception(UiBot.GetString("Mage/CursorPositionTypeErr"))
        return cursor_position

    def get_x_offset_param(self, option):
        x_offset = option.get('iCursorOffsetX', 0)
        if not isinstance(x_offset, int):
            raise Exception(UiBot.GetString("Mage/CursorOffsetXTypeErr"))
        return x_offset

    def get_y_offset_param(self, option):
        y_offset = option.get('iCursorOffsetY', 0)
        if not isinstance(y_offset, int):
            raise Exception(UiBot.GetString("Mage/CursorOffsetYTypeErr"))
        return y_offset

    def get_modifier_key_param(self, option):
        modifier_key = option.get('sKeyModifiers', [])
        if not isinstance(modifier_key, list):
            raise Exception(UiBot.GetString("Mage/ModifierKeyTypeErr"))
        return modifier_key

    def get_password_param(self, option):
        password = option.get('password', None)
        if not isinstance(password, str):
            raise Exception(UiBot.GetString('Mage/PasswordTypeErr'))
        return password

#-------------add by www-----------
    def get_valid_file_param(self, file):                
        if not os.path.exists(file):
            raise Exception("{0} {1}".format(file, UiBot.GetString("Mage/FileNotExist")))
        elif not os.path.isfile(file):
            raise Exception("{0} {1}".format(file, UiBot.GetString("File/ParamCheck/InvalidFilePath")))
        else:
            size = os.path.getsize(file)
            # 文件大小不能超过10M
            if size > (1024 * 1024 * 20):
                raise Exception("{0} {1}".format(file, UiBot.GetString("RpaCollaboration/FileTooLarge")))
            elif size <= 0:
                raise Exception("{0} {1}".format(file, UiBot.GetString("RpaCollaboration/FileIsEmpty")))
            else:
                _, ext = os.path.splitext(file)
                # if ext not in ['.jpeg', '.jpg', '.png', '.bmp', '.tiff', '.tif','.doc','.docx', '.pdf','.ofd']:
                #     raise Exception("{0} {1}".format(file, UiBot.GetString("RpaCollaboration/FileTypeNotSupport")))
                # if ext == '.txt':#文本文件类型，则判断下文本字符串长度
                #     try:
                #         with open(file, "r", encoding="utf-8") as f:
                #             text = f.read()
                #             if len(text) > 30000:
                #                 raise Exception(UiBot.GetString("Mage/TextSizeTooLong"))
                #     except Exception as ex:
                #         raise Exception("{0} {1}{2}".format(file, UiBot.GetString("Mage/OpenFileErr"), ex))
        return file
#通用的功能函数实现
def UdpLog(msg):
    pass

def generate_image_name():
    filename = str(uuid.uuid4())
    filename = filename.replace('-', 'X')
    tmppath = os.environ.get('TEMP', None)
    if tmppath == None:
        tmppath = os.environ.get('TMP', None)
        if tmppath == None:
            if _system == 'linux':
                if os.path.isdir('/tmp'):
                    tmppath = '/tmp'
                else:
                    return None
            else:
                return None
    if len(tmppath) == 0:
        return None
    else:
        return os.path.join(tmppath, filename + '.png')

def generate_pdf_name():
    filename = str(uuid.uuid4())
    filename = filename.replace('-', 'X')
    tmppath = os.environ.get('TEMP', None)
    if tmppath == None:
        tmppath = os.environ.get('TMP', None)
        if tmppath == None:
            if _system == 'linux':
                if os.path.isdir('/tmp'):
                    tmppath = '/tmp'
                else:
                    return None
            else:
                return None
    if len(tmppath) == 0:
        return None
    else:
        return os.path.join(tmppath, filename + '.pdf')

def delete_file(filename):
    try:
        os.remove(filename)
    except Exception as identifier:
        pass

def time_delay(millsec):
    try:
        millsec_left = millsec
        while(millsec_left > 0 and (not UiBot.IsStop())):
            if millsec_left > 1000:
                time.sleep(1)
                millsec_left = millsec_left - 1000
            else:
                time.sleep(millsec_left / 1000)
                millsec_left = 0
    except Exception as identifier:
        pass

if _system == 'windows':
    def set_foreground_window(hwnd, active_window, shell, bdesktop):
        while hwnd != 0:
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            if style & win32con.WS_CHILD:
                hwnd = win32gui.GetParent(hwnd)
            else:
                clsname = win32gui.GetClassName(hwnd)
                if clsname == 'WorkerW' or clsname == 'Progman':
                    UdpLog('{:#x} maybe desktop'.format(hwnd))
                    if active_window and bdesktop == False:
                        if shell == None:
                            shell = win32com.client.Dispatch("Shell.Application")
                        shell.ToggleDesktop()
                        win32gui.UpdateWindow(hwnd)
                        time.sleep(500/1000)
                        if win32gui.GetForegroundWindow() == hwnd:
                            UdpLog('ToggleDesktop ok')
                        else:
                            UdpLog('ToggleDesktop fail')
                        bdesktop = True
                else:
                    if active_window:
                        if win32gui.IsIconic(hwnd):
                            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                            time.sleep(500 / 1000)
                        if win32gui.GetForegroundWindow() != hwnd:
                            try:
                                dwStyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOMOVE)
                                if not ((dwStyle & win32con.WS_EX_TOPMOST) == win32con.WS_EX_TOPMOST):
                                    win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOMOVE)
                                time.sleep(500 / 1000)
                            except Exception as e:
                                shell = win32com.client.Dispatch("WScript.Shell")
                                shell.SendKeys('{SCROLLLOCK}')
                                time.sleep(0.2)
                                shell.SendKeys('{SCROLLLOCK}')
                                win32gui.SetForegroundWindow(hwnd)
                                win32gui.UpdateWindow(hwnd)
                                time.sleep(500 / 1000)
                break
        return shell, bdesktop, hwnd
else:
    def set_foreground_window(hwnd, active_window, shell, bdesktop):
        ImageHelper.ActiveWindow(hwnd)
        return shell, bdesktop, hwnd

def calculate_rect(ele_rect, _x, _y, _width, _height):
    jo = json.loads(ele_rect)
    if 'x' not in jo or 'y' not in jo or 'width' not in jo or 'height' not in jo:
        raise Exception(UiBot.GetString("Mage/WindowArea"))
    window_x = jo['x']
    window_y = jo['y']
    window_width = jo['width']
    window_height = jo['height']
    if window_width == 0 or window_height == 0:
        raise Exception(UiBot.GetString("Mage/WindowArea"))
    if _width != 0 and _height != 0 and _x >= 0 and _y >= 0:
        x = window_x + _x
        y = window_y + _y
        width = _width
        height = _height
    else:
        x = window_x
        y = window_y
        width = window_width
        height = window_height
    return window_x, window_y, x, y, width, height

def screen_shot(element, x, y, width, height, active_window, time_out):
    shell = None
    filename = None
    bdesktop = False
    UiBot.PushContext()
    try:
        if active_window:
            print("call->FindAndActiveElement")
            ele = UiBot.InvokeRobotCore(0, 'FindAndActiveElement', [element, time_out])
        else:
            ele = UiBot.InvokeRobotCore(0, 'FindElement', [element, time_out])
        if ele == None or ele <= 0:
            raise Exception(UiBot.GetString("Mage/ElementNotFound"))
        hwnd = UiBot.InvokeRobotCore(ele, 'GetValidHandle', [])
        if hwnd <= 0:
            raise Exception(UiBot.GetString("Mage/WindowNotFound"))
        shell, bdesktop, hwnd = set_foreground_window(hwnd, active_window, shell, bdesktop)
        if hwnd <= 0:
            raise Exception(UiBot.GetString("Mage/ActiveWindow"))
        ele_rect = UiBot.InvokeRobotCore(ele, 'UiElementGetRect', ['screen', ''])
        print(ele_rect)
        window_x, window_y, x, y, width, height = calculate_rect(ele_rect, x, y, width, height)

        filename = generate_image_name()
        if filename == None:
            raise Exception(UiBot.GetString("Mage/GenerateImageNameFail"))

        succ = ImageHelper.CreateImage(filename, x, y, x + width - 1, y + height - 1)
        if succ < 0:
            raise Exception(UiBot.GetString("Mage/ScreenShotFail"))

    except Exception as e:
        UiBot.PopContext()
        msg = '{0}'.format(e)
        raise Exception(msg)

    UiBot.PopContext()
    return shell, filename

def check_correct_state(result_json):
    if "code" in result_json and "message" in result_json:
        code = result_json.get('code')
        msg = result_json.get('message')
        if code != 0:
            if code == 10011:
                #账号配额不足（10011），提示信息进行提升配额的引导
                raise Exception(UiBot.GetString("Mage/HTTP_RECG_FAILED") + '{0}'.format(msg) + ';  ' + UiBot.GetString("Mage/MageUpgradePool"))
            elif code == 10015:
                #账号调用频率超限（10015），提示信息进行升级的引导
                raise Exception(UiBot.GetString("Mage/HTTP_RECG_FAILED") + '{0}'.format(msg) + ';  ' + UiBot.GetString("Mage/MageUpgrade"))
            else:
                raise Exception(UiBot.GetString("Mage/HTTP_RECG_FAILED") + '{0}'.format(msg))
    else:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))

def process_text_result(result_json, page_number):
    check_correct_state(result_json)
    if "data" not in result_json:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    if "items" not in result_json["data"]:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    if "struct_content" not in result_json["data"]:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    if "page" not in result_json["data"]["struct_content"]:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    if "paragraph" not in result_json["data"]["struct_content"]:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    if "row" not in result_json["data"]["struct_content"]:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))

    result_json["data"]["ai_function"] = "ocr_text"
    #添加页码信息
    for item in result_json["data"]["items"]:
        item["page_number"] = page_number
    for item in result_json["data"]["struct_content"]["page"]:
        item["page_number"] = page_number
    for item in result_json["data"]["struct_content"]["paragraph"]:
        item["page_number"] = page_number
    for item in result_json["data"]["struct_content"]["row"]:
        item["page_number"] = page_number
    return result_json["data"]

def process_table_result(result_json, page_number):
    check_correct_state(result_json)
    if "data" not in result_json:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    if "tables" not in result_json["data"]:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    if "items" not in result_json["data"]:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))

    tables_result = dict()
    tables_result["ai_function"] = "ocr_table"
    tables_result["tables"] = result_json["data"]["tables"]
    tables_result["items"] = result_json["data"]["items"]
    for item in tables_result["tables"]:
        item["page_number"] = page_number
    for item in tables_result["items"]:
        item["page_number"] = page_number
    return tables_result

def process_invoice_result(result_json, page_number):
    check_correct_state(result_json)
    if "data" not in result_json:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    if "result" not in result_json["data"]:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    if "result" not in result_json["data"]["result"]:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    invoice_array = result_json["data"]["result"]["result"]
    for item in invoice_array:
        item["ai_function"] = "ocr_invoice"
        item["page_number"] = page_number
    return invoice_array

def process_card_result(result_json, page_number):
    check_correct_state(result_json)
    if "data" not in result_json:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    result_json["data"]["ai_function"] = "ocr_card"
    result_json["data"]["page_number"] = page_number
    return result_json["data"]

# add by CaiCQ
def process_stamp_result(result_json):
    check_correct_state(result_json)
    if "data" not in result_json:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    if "stamps" not in result_json['data']:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    result_json["data"]["ai_function"] = "ocr_stamp"

    return result_json['data']
################

def process_verify_code_result(result_json):
    check_correct_state(result_json)
    if "data" not in result_json:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    result = result_json["data"]["result"]
    if len(result) == 0:#将二维滑块验证码数据取出
        if "positions" not in result_json["data"]:
            raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
        positions = result_json["data"]["positions"]
        if len(positions) != 0:#数组不为空
            result = positions
    return result

def process_addr_std_result(result_json):
    check_correct_state(result_json)
    if "data" not in result_json:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    if "geo_list" not in result_json["data"]:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    geo_array = result_json["data"]["geo_list"]
    for item in geo_array:
        item["ai_function"] = "nlp_addr_std"
    return geo_array

def process_text_classify_result(result_json):
    check_correct_state(result_json)
    if "data" not in result_json:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    if "results" not in result_json["data"]:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    classify_array = result_json["data"]["results"]
    for item in classify_array:
        item["ai_function"] = "nlp_text_classify"
    return classify_array

def check_update_time_is_conflict(func, line_num, update_time_design, update_time_run):
    if update_time_design != update_time_run:
        print("#####WARNNING#####:[{0}]The update time between design state and running state is different!".format(func))
        #UiBot.TracePrint(func, line_num, UiBot.GetString("Mage/UpdateTimeMatchFail"))
        UiBot.Log("", 0, 1, UiBot.GetString("Mage/UpdateTimeMatchFail").format(func))

def process_text_extract_result(result_json):
    check_correct_state(result_json)
    if "data" not in result_json:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    if "results" not in result_json["data"]:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    extract_result_array = result_json["data"]["results"]
    update_time_str = result_json["data"]["update_time"]
    format_update_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(update_time_str)))
    for item in extract_result_array:
        item["ai_function"] = "nlp_text_extract"
        item["update_time"] = format_update_time_str
    return extract_result_array

def process_ocr_template_result(result_json, page_number):
    check_correct_state(result_json)
    if "data" not in result_json:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    result_json["data"]["ai_function"] = "ocr_template"
    result_json["data"]["page_number"] = page_number
    update_time_str = result_json["data"]["update_time"]
    format_update_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(update_time_str)))
    result_json["data"]["update_time"] = format_update_time_str
    return result_json["data"]

def process_query_recognizer_result(result_json):
    check_correct_state(result_json)
    if "data" not in result_json:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    recognizer_info_arr = result_json.get("data")
    if len(recognizer_info_arr) <= 0:
        raise Exception(UiBot.GetString("Mage/LogRecord/QueryRecognizerErr"))
    return _SafeGetValue(recognizer_info_arr[0], "left_quota")

def get_extract_version_hash_from_net_result(result_json):
    check_correct_state(result_json)
    if "data" not in result_json:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    res_data = result_json.get("data")
    if "versions" not in res_data:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    published_version_list = list(
        filter(lambda item: 4 == item['status'] if type(item) is dict else False, res_data["versions"]))
    if len(published_version_list) == 0:
        raise Exception(UiBot.GetString("Mage/TextExtractNoPublishedVersion"))
    return published_version_list[0]["version_hash"]

def get_extract_templates_list_from_net_result(result_json):
    check_correct_state(result_json)
    if "data" not in result_json:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    res_data = result_json.get("data")
    if "templates" not in res_data:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    return res_data["templates"], res_data["total_count"]

def get_extract_field_list(merge_templates_list, template_name):
    template_list = list(
        filter(lambda item: template_name == item['name'] if type(item) is dict else False, merge_templates_list))
    if len(template_list) == 0:
        raise Exception(UiBot.GetString("Mage/TemplateNoMatched").format(template_name))
    return list(map(lambda x: x["name"], template_list[0]["output_fields"]))

def get_template_template_list_from_net_result(result_json):
    check_correct_state(result_json)
    if "data" not in result_json:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    res_data = result_json.get("data")
    if "templates" not in res_data:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    return res_data["templates"], res_data["total_count"]

def get_template_filed_list(merge_templates_list, template_name):
    template_list = list(
        filter(lambda item: template_name == item['name'] if type(item) is dict else False, merge_templates_list))
    if len(template_list) == 0:
        raise Exception(UiBot.GetString("Mage/TemplateNoMatched").format(template_name))
    return list(map(lambda x: x["name"], template_list[0]["fields"]))

def merge_text_result_for_pdf(list_page_result):
    merge_result = dict()
    merge_result["ai_function"] = "ocr_text"
    merge_text_list = list()
    merge_page_list = list()
    merge_paragraph_list = list()
    merge_row_list = list()
    for page_result in list_page_result:
        for text_item in page_result["items"]:
            merge_text_list.append(text_item)
        for page_item in page_result["struct_content"]["page"]:
            merge_page_list.append(page_item)
        for paragraph_item in page_result["struct_content"]["paragraph"]:
            merge_paragraph_list.append(paragraph_item)
        for row_item in page_result["struct_content"]["row"]:
            merge_row_list.append(row_item)
    merge_result["items"] = merge_text_list
    struct_content_dict = dict()
    struct_content_dict["page"] = merge_page_list
    struct_content_dict["paragraph"] = merge_paragraph_list
    struct_content_dict["row"] = merge_row_list
    merge_result["struct_content"] = struct_content_dict
    return merge_result

def merge_invoice_result_for_pdf(list_page_result):
    merge_result = [invoice_item for page_result in list_page_result for invoice_item in page_result]
    return merge_result

def merge_table_result_for_pdf(list_page_result):
    merge_result = dict()
    merge_result["ai_function"] = "ocr_table"
    merge_tables = list()
    merge_texts = list()
    for page_result in list_page_result:
        for table_item in page_result["tables"]:
            merge_tables.append(table_item)
        for table_item in page_result["items"]:
            merge_texts.append(table_item)
    merge_result["tables"] = merge_tables
    merge_result["items"] = merge_texts
    return merge_result

def merge_stamp_result_for_pdf(list_stamp_result):
    merge_result = dict()
    merge_result['ai_function'] = 'ocr_stamp'
    merge_stamps = list()
    for single_stamp_result in list_stamp_result:
        merge_stamps.extend(single_stamp_result['stamps'])
    merge_result['stamps'] = merge_stamps
    return merge_result


def process_pdf_result(ai_function, list_page_result):
    if ai_function == "ocr_table":
        return merge_table_result_for_pdf(list_page_result)
    elif ai_function == "ocr_text":
        return merge_text_result_for_pdf(list_page_result)
    elif ai_function == 'ocr_stamp':
        return merge_stamp_result_for_pdf(list_page_result)
    elif ai_function == "ocr_card":
        return list_page_result
    elif ai_function == "ocr_invoice":
        return merge_invoice_result_for_pdf(list_page_result)
    elif ai_function == "ocr_template":
        return list_page_result
    else:
        raise Exception(UiBot.GetString("Mage/UnKnownAiFunction"))

default_option = {"bContinueOnError":0,
                  "iDelayAfter":300,
                  "iDelayBefore":200,
                  "bSetForeground":1}

def process_task_result(result_json):
    check_correct_state(result_json)
    if "task_id" not in result_json:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))

    return result_json["task_id"]


def process_idp_page_result(result_json):
    check_correct_state(result_json)
    if "data" not in result_json:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
    if "fields" not in result_json["data"]:
        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))

    retData = []
    fields = result_json["data"]["fields"]
    for val in fields:
        name = _SafeGetValue(val, "name")
        retData.append(name)

    return retData

################################################################################################
#    API命令的实现
################################################################################################
def ImageOCRText(_file_path_name, _mage_cfg, _time_out):
    pubkey, secret, base_url = r'', r'', r''
    log_record = LogRecord()
    try:
        #解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        file_path_name = param_util.get_file_name_param(_file_path_name)
        time_out = param_util.get_time_out_param(_time_out)
        #构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body(file_path_name, True, "list")
        start_time = datetime.datetime.now()
        retry_num = 3
        res_data = None
        for i in range(retry_num):#重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['text'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:#重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        #简单地后处理网络返回的响应消息
        text_recg_result = process_text_result(res_data, 1)
        log_record.upload_log(pubkey, secret, 1, 'ImageOcrText', base_url)
        return text_recg_result
    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'ImageOcrText', base_url)
        msg = '{0}'.format(e)
        raise Exception(msg)

def ScreenOCRText(_element, _rect, _mage_cfg, _time_out, _option= default_option, with_char_info=False):
    shell = None
    file_path_name = None
    err_msg = None
    continue_on_err = False
    text_recg_result = dict()
    pubkey, secret, base_url = r'', r'', r''
    log_record = LogRecord()
    try:
        # 解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        element = param_util.get_element_param(_element)
        x, y, width, height = param_util.get_rect_param(_rect)
        time_out = param_util.get_time_out_param(_time_out)
        option = param_util.get_option_param(_option)
        delay_before, delay_after = param_util.get_delay_param(option)
        continue_on_err = param_util.get_continue_on_err_param(option)
        active_window = param_util.get_active_window_param(option)
        if not isinstance(with_char_info, bool):
            with_char_info = False

        time_delay(delay_before)
        start_time = datetime.datetime.now()
        shell, file_path_name = screen_shot(element, x, y, width, height, active_window, time_out)
        # 构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body(file_path_name, True, "list", with_char_info)
        retry_num = 3
        res_data = None
        for i in range(retry_num):  # 重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['text'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:  # 重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        # 简单地后处理网络返回的响应消息
        text_recg_result = process_text_result(res_data, 1)
        time_delay(delay_after)
        log_record.upload_log(pubkey, secret, 1, 'ScreenOCRText', base_url)
    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'ScreenOCRText', base_url)
        err_msg = str(e)

    if file_path_name != None:
        delete_file(file_path_name)
    if shell != None:
        shell.ToggleDesktop()
    if err_msg != None:
        if continue_on_err == False:
            raise Exception(err_msg)
        else:
            return text_recg_result
    else:
        return text_recg_result

def ImageOCRTable(_file_path_name, _mage_cfg, _time_out):
    pubkey, secret, base_url = r'', r'', r''
    log_record = LogRecord()
    try:
        #解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        file_path_name = param_util.get_file_name_param(_file_path_name)
        time_out = param_util.get_time_out_param(_time_out)
        #构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body(file_path_name, None, "list")
        start_time = datetime.datetime.now()
        retry_num = 3
        res_data = None
        for i in range(retry_num):#重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['table'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:#重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        #简单地后处理网络返回的响应消息
        table_recg_result = process_table_result(res_data, 1)
        log_record.upload_log(pubkey, secret, 1, 'ImageOcrTable', base_url)
        return table_recg_result
    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'ImageOcrTable', base_url)
        msg = '{0}'.format(e)
        raise Exception(msg)

def ScreenOCRTable(_element, _rect, _mage_cfg, _time_out, _option= default_option):
    shell = None
    file_path_name = None
    err_msg = None
    continue_on_err = False
    table_recg_result = []
    pubkey, secret, base_url = r'', r'', r''
    log_record = LogRecord()
    try:
        # 解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        element = param_util.get_element_param(_element)
        x, y, width, height = param_util.get_rect_param(_rect)
        time_out = param_util.get_time_out_param(_time_out)
        option = param_util.get_option_param(_option)
        delay_before, delay_after = param_util.get_delay_param(option)
        continue_on_err = param_util.get_continue_on_err_param(option)
        active_window = param_util.get_active_window_param(option)

        time_delay(delay_before)
        start_time = datetime.datetime.now()
        shell, file_path_name = screen_shot(element, x, y, width, height, active_window, time_out)
        # 构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body(file_path_name, None, "list")
        retry_num = 3
        res_data = None
        for i in range(retry_num):  # 重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['table'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:  # 重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        # 简单地后处理网络返回的响应消息
        table_recg_result = process_table_result(res_data, 1)
        time_delay(delay_after)
        log_record.upload_log(pubkey, secret, 1, 'ScreenOCRTable', base_url)
    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'ScreenOCRTable', base_url)
        err_msg = str(e)

    if file_path_name != None:
        delete_file(file_path_name)
    if shell != None:
        shell.ToggleDesktop()
    if err_msg != None:
        if continue_on_err == False:
            raise Exception(err_msg)
        else:
            return table_recg_result
    else:
        return table_recg_result

def ImageOCRInvoice(_file_path_name, _mage_cfg, _time_out):
    pubkey, secret, base_url = r'', r'', r''
    log_record = LogRecord()
    try:
        #解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        file_path_name = param_util.get_file_name_param(_file_path_name)
        time_out = param_util.get_time_out_param(_time_out)
        #构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body(file_path_name, None, "str")
        start_time = datetime.datetime.now()
        retry_num = 3
        res_data = None
        for i in range(retry_num):#重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['bill'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:#重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        #简单地后处理网络返回的响应消息
        invoice_recg_result = process_invoice_result(res_data, 1)
        log_record.upload_log(pubkey, secret, 1, 'ImageOcrInvoice', base_url)
        return invoice_recg_result
    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'ImageOcrInvoice', base_url)
        msg = '{0}'.format(e)
        raise Exception(msg)

def ScreenOCRInvoice(_element, _rect, _mage_cfg, _time_out, _option= default_option):
    shell = None
    file_path_name = None
    err_msg = None
    continue_on_err = False
    invoice_recg_result = []
    pubkey, secret, base_url = r'', r'', r''
    log_record = LogRecord()
    try:
        # 解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        element = param_util.get_element_param(_element)
        x, y, width, height = param_util.get_rect_param(_rect)
        time_out = param_util.get_time_out_param(_time_out)
        option = param_util.get_option_param(_option)
        delay_before, delay_after = param_util.get_delay_param(option)
        continue_on_err = param_util.get_continue_on_err_param(option)
        active_window = param_util.get_active_window_param(option)

        time_delay(delay_before)
        start_time = datetime.datetime.now()
        shell, file_path_name = screen_shot(element, x, y, width, height, active_window, time_out)
        # 构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body(file_path_name, None, "str")
        retry_num = 3
        res_data = None
        for i in range(retry_num):  # 重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['bill'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:  # 重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        # 简单地后处理网络返回的响应消息
        invoice_recg_result = process_invoice_result(res_data, 1)
        time_delay(delay_after)
        log_record.upload_log(pubkey, secret, 1, 'ScreenOCRInvoice', base_url)
    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'ScreenOCRInvoice', base_url)
        err_msg = str(e)

    if file_path_name != None:
        delete_file(file_path_name)
    if shell != None:
        shell.ToggleDesktop()
    if err_msg != None:
        if continue_on_err == False:
            raise Exception(err_msg)
        else:
            return invoice_recg_result
    else:
        return invoice_recg_result

def ImageOCRCard(_file_path_name, _mage_cfg, _time_out):
    pubkey, secret, base_url = r'', r'', r''
    log_record = LogRecord()
    try:
        #解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        file_path_name = param_util.get_file_name_param(_file_path_name)
        time_out = param_util.get_time_out_param(_time_out)
        #构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body(file_path_name, None, "str")
        start_time = datetime.datetime.now()
        retry_num = 3
        res_data = None
        for i in range(retry_num):#重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['card'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:#重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        #简单地后处理网络返回的响应消息
        card_recg_result = process_card_result(res_data, 1)
        log_record.upload_log(pubkey, secret, 1, 'ImageOcrCard', base_url)
        return card_recg_result
    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'ImageOcrCard', base_url)
        msg = '{0}'.format(e)
        raise Exception(msg)

def ScreenOCRCard(_element, _rect, _mage_cfg, _time_out, _option= default_option):
    shell = None
    file_path_name = None
    err_msg = None
    continue_on_err = False
    card_recg_result = dict()
    pubkey, secret, base_url = r'', r'', r''
    log_record = LogRecord()
    try:
        # 解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        element = param_util.get_element_param(_element)
        x, y, width, height = param_util.get_rect_param(_rect)
        time_out = param_util.get_time_out_param(_time_out)
        option = param_util.get_option_param(_option)
        delay_before, delay_after = param_util.get_delay_param(option)
        continue_on_err = param_util.get_continue_on_err_param(option)
        active_window = param_util.get_active_window_param(option)

        time_delay(delay_before)
        start_time = datetime.datetime.now()
        shell, file_path_name = screen_shot(element, x, y, width, height, active_window, time_out)
        # 构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body(file_path_name, None, "str")
        retry_num = 3
        res_data = None
        for i in range(retry_num):  # 重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['card'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:  # 重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        # 简单地后处理网络返回的响应消息
        card_recg_result = process_card_result(res_data, 1)
        time_delay(delay_after)
        log_record.upload_log(pubkey, secret, 1, 'ScreenOCRCard', base_url)
    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'ScreenOCRCard', base_url)
        err_msg = str(e)

    if file_path_name != None:
        delete_file(file_path_name)
    if shell != None:
        shell.ToggleDesktop()
    if err_msg != None:
        if continue_on_err == False:
            raise Exception(err_msg)
        else:
            return card_recg_result
    else:
        return card_recg_result

def _Decrypt(pwd):
    UiBot.PushContext()
    try:
        #解密失败 抛出异常
        pwd = UiBot.InvokeRobotCore(0, 'GetStringFromSecText', ['',pwd])
    except:
        pass
    UiBot.PopContext()
    return pwd

def PDFOCRTable(_mage_cfg, _pdf_file_path_name, _password, _is_all_page, _page_cfg, _interval_time, _time_out):
    ai_function = "ocr_table"
    _password = _Decrypt(_password)
    return _OCRPDF(_mage_cfg, _pdf_file_path_name, _password, _is_all_page, _page_cfg, _interval_time, _time_out, ai_function)

def PDFOCRText(_mage_cfg, _pdf_file_path_name, _password, _is_all_page, _page_cfg, _interval_time, _time_out):
    ai_function = "ocr_text"
    _password = _Decrypt(_password)
    return _OCRPDF(_mage_cfg, _pdf_file_path_name, _password, _is_all_page, _page_cfg, _interval_time, _time_out, ai_function)

def PDFOCRInvoice(_mage_cfg, _pdf_file_path_name, _password, _is_all_page, _page_cfg, _interval_time, _time_out):
    ai_function = "ocr_invoice"
    _password = _Decrypt(_password)
    return _OCRPDF(_mage_cfg, _pdf_file_path_name, _password, _is_all_page, _page_cfg, _interval_time, _time_out, ai_function)

def PDFOCRCard(_mage_cfg, _pdf_file_path_name, _password, _is_all_page, _page_cfg, _interval_time, _time_out):
    ai_function = "ocr_card"
    _password = _Decrypt(_password)
    return _OCRPDF(_mage_cfg, _pdf_file_path_name, _password, _is_all_page, _page_cfg, _interval_time, _time_out, ai_function)

# ----> add by Cai CQ on 2021-05-14
def PDFOCRStamp(_pdf_file_path_name, _mage_cfg, _is_all_page, _page_cfg, _interval_time, _time_out, _option={'password': ''}):
    param_util = ParamUtil()
    option = param_util.get_option_param(_option)
    password = param_util.get_password_param(option)
    password = _Decrypt(password)
    ai_function = "ocr_stamp"
    return _OCRPDF(_mage_cfg, _pdf_file_path_name, password, _is_all_page, _page_cfg, _interval_time, _time_out, ai_function)

# <---------

def PDFOCRTemplate(_mage_cfg, _pdf_file_path_name, _password, _is_all_page, _page_cfg, _interval_time, _time_out):
    ai_function = "ocr_template"
    _password = _Decrypt(_password)
    return _OCRPDF(_mage_cfg, _pdf_file_path_name, _password, _is_all_page, _page_cfg, _interval_time, _time_out, ai_function)

def _OCRPDF(_mage_cfg, _pdf_file_path_name, _password, _is_all_page, _page_cfg, _interval_time, _time_out, ai_function):
    filename = None
    doc = None
    pubkey, secret, base_url = r'', r'', r''
    log_record = LogRecord()
    try:
        #解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        password = param_util.get_password(_password)
        b_is_all_page = param_util.get_pdf_all_page_status(_is_all_page)
        pdf_file_path_name = param_util.get_pdf_file_name_param(_pdf_file_path_name)
        time_out = param_util.get_time_out_param(_time_out)
        interval_time = param_util.get_interval_time_param(_interval_time)
        url_route = url_route_dict['text']
        if ai_function == "ocr_table":
            url_route = url_route_dict['table']
        elif ai_function == "ocr_text":
            url_route = url_route_dict['text']
        elif ai_function == "ocr_card":
            url_route = url_route_dict['card']
        elif ai_function == "ocr_invoice":
            url_route = url_route_dict['bill']
        elif ai_function == "ocr_template":
            url_route = url_route_dict['ocr_template']
        elif ai_function == "ocr_stamp":
            url_route = url_route_dict['stamp']
        else:
            raise Exception(UiBot.GetString("Mage/UnKnownAiFunction"))

        #打开PDF文件
        try:
            doc = fitz.open(pdf_file_path_name)
        except Exception as e:
            print("OCRPDF-->fitz.open err!")
            raise Exception(UiBot.GetString("Mage/NotPDFFile"))
        if _system == 'windows':
            if not doc.isPDF:
                print("OCRPDF-->is not a PDF File!")
                raise Exception(UiBot.GetString("Mage/NotPDFFile"))
        else:
            if not doc.is_pdf:
                print("OCRPDF-->is not a PDF File!")
                raise Exception(UiBot.GetString("Mage/NotPDFFile"))
        if doc.permissions == 0:
            #加密的pdf
            print("OCRPDF-->PDF isEncrypted!")
            val = doc.authenticate(password)
            if not val:
                print("OCRPDF-->Decrypted failed!")
                raise Exception(UiBot.GetString("Mage/DecryptedPDFFileFailed"))
        page_count = doc.page_count
        if not b_is_all_page:
            page_list = param_util.get_pdf_page_cfg(_page_cfg, page_count)
        else:
            page_list = [pg for pg in range(1, page_count + 1)]
        print("page_list:{0}".format(page_list))

        pdf_recg_result = []
        for pg in page_list:
            if UiBot.IsStop():
                break
            start_time = datetime.datetime.now()
            upload_img = False
            if upload_img:#上传图片识别
                page = doc[pg - 1]
                trans = fitz.Matrix(2.0, 2.0).prerotate(0)  # 尺寸放大2倍
                pm = page.get_pixmap(matrix=trans, alpha=False)
                filename = generate_image_name()
                if filename == None:
                    raise Exception(UiBot.GetString("Mage/GenerateImageNameFail"))
                pm.save(filename, "png")
                print("Upload image file to recg PDF, page:{0}".format(pg))
            else:#上传pdf文件识别
                filename = generate_pdf_name()
                if filename == None:
                    raise Exception(UiBot.GetString("Mage/GenerateImageNameFail"))
                if _system == 'windows':
                    with fitz.open() as fp_slice:
                        fp_slice.insert_pdf(doc, pg - 1, pg - 1)
                        fp_slice.save(filename)
                else:
                    fp_slice = fitz.open()
                    fp_slice.insert_pdf(doc, pg - 1, pg - 1)
                    fp_slice.save(filename)
                    fp_slice.close()
                print("Upload slice pdf file to recg PDF, page:{0}".format(pg))

            #构造并发送网络请求
            mage_client = MageClient(base_url)
            msg_header = mage_client.generate_header(pubkey, secret)
            if ai_function == "ocr_table":
                msg_body = mage_client.generate_body(filename, None, "list")
            elif ai_function == "ocr_text":
                msg_body = mage_client.generate_body(filename, True, "list")
            elif ai_function == "ocr_card":
                msg_body = mage_client.generate_body(filename, None, "str")
            elif ai_function == "ocr_invoice":
                msg_body = mage_client.generate_body(filename, None, "str")
            elif ai_function == "ocr_stamp":
                msg_body = mage_client.generate_body(filename, None, "str")
            elif ai_function == "ocr_template":
                msg_body = mage_client.generate_body_for_template(filename)
            else:
                raise Exception(UiBot.GetString("Mage/UnKnownAiFunction"))

            retry_num = 3
            res_data = None
            for i in range(retry_num):#重试3次
                try:
                    left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                    if left_time_out <= 0:
                        i = retry_num - 1
                        raise Exception(UiBot.GetString("Mage/TimeOut"))
                    res_data = mage_client.do_request(url_route, msg_header, msg_body, left_time_out)
                    break
                except Exception as e:
                    if i == retry_num - 1:#重试结束，若仍报错，则把异常抛出，让外面捕获处理
                        raise Exception('{0}'.format(e))
                    pass
            #简单地后处理网络返回的响应消息
            if ai_function == "ocr_table":
                single_page_result = process_table_result(res_data, pg)
            elif ai_function == "ocr_text":
                single_page_result = process_text_result(res_data, pg)
            elif ai_function == "ocr_card":
                single_page_result = process_card_result(res_data, pg)
            elif ai_function == "ocr_invoice":
                single_page_result = process_invoice_result(res_data, pg)
            elif ai_function == "ocr_stamp":
                single_page_result = process_stamp_result(res_data)
            elif ai_function == "ocr_template":
                single_page_result = process_ocr_template_result(res_data, pg)
            else:
                raise Exception(UiBot.GetString("Mage/UnKnownAiFunction"))

            pdf_recg_result.append(single_page_result)
            delete_file(filename)
            filename = None
            if pg != page_list[-1]:
                time_delay(interval_time)
        log_record.upload_log(pubkey, secret, 1, 'OCRPDF', base_url)
        return process_pdf_result(ai_function, pdf_recg_result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        log_record.upload_log(pubkey, secret, 0, 'OCRPDF', base_url)
        if filename is not None:
            delete_file(filename)
            filename = None
        msg = '{0}'.format(e)
        raise Exception(msg)
    finally:
        if doc is not None:
            doc.close()

def ImageOCRVerifyCode(_file_path_name, _mage_cfg, _time_out):
    pubkey, secret, base_url = r'', r'', r''
    log_record = LogRecord()
    try:
        # 解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        file_path_name = param_util.get_file_name_param(_file_path_name)
        time_out = param_util.get_time_out_param(_time_out)
        # 构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body(file_path_name, None, "str")
        start_time = datetime.datetime.now()
        retry_num = 3
        res_data = None
        for i in range(retry_num):  # 重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['verify_code'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:  # 重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        # 简单地后处理网络返回的响应消息
        verify_code_recg_result = process_verify_code_result(res_data)
        log_record.upload_log(pubkey, secret, 1, 'ImageOCRVerifyCode', base_url)
        return verify_code_recg_result
    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'ImageOCRVerifyCode', base_url)
        msg = '{0}'.format(e)
        raise Exception(msg)

def ScreenOCRVerifyCode(_element, _rect, _mage_cfg, _time_out, _option=default_option):
    shell = None
    file_path_name = None
    err_msg = None
    continue_on_err = False
    pubkey, secret, base_url = r'', r'', r''
    log_record = LogRecord()
    verify_code_recg_result = ''
    try:
        # 解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        element = param_util.get_element_param(_element)
        x, y, width, height = param_util.get_rect_param(_rect)
        time_out = param_util.get_time_out_param(_time_out)
        option = param_util.get_option_param(_option)
        delay_before, delay_after = param_util.get_delay_param(option)
        continue_on_err = param_util.get_continue_on_err_param(option)
        active_window = param_util.get_active_window_param(option)

        time_delay(delay_before)
        start_time = datetime.datetime.now()
        shell, file_path_name = screen_shot(element, x, y, width, height, active_window, time_out)
        # 构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body(file_path_name, None, "str")
        retry_num = 3
        res_data = None
        for i in range(retry_num):  # 重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['verify_code'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:  # 重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        # 简单地后处理网络返回的响应消息
        verify_code_recg_result = process_verify_code_result(res_data)
        time_delay(delay_after)
        log_record.upload_log(pubkey, secret, 1, 'ScreenOCRVerifyCode', base_url)
    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'ScreenOCRVerifyCode', base_url)
        err_msg = str(e)

    if file_path_name != None:
        delete_file(file_path_name)
    if shell != None:
        shell.ToggleDesktop()
    if err_msg != None:
        if continue_on_err == False:
            raise Exception(err_msg)
        else:
            return verify_code_recg_result
    else:
        return verify_code_recg_result

def NLPAddressStandard(_address, _mage_cfg, _time_out):
    pubkey, secret, base_url = r'', r'', r''
    log_record = LogRecord()
    try:
        # 解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        address = param_util.get_address(_address)
        time_out = param_util.get_time_out_param(_time_out)
        # 构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body_for_text(address)
        start_time = datetime.datetime.now()
        retry_num = 3
        res_data = None
        for i in range(retry_num):  # 重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['addr_std'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:  # 重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        # 简单地后处理网络返回的响应消息
        result = process_addr_std_result(res_data)
        log_record.upload_log(pubkey, secret, 1, 'NLPAddressStandard', base_url)
        return result
    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'NLPAddressStandard', base_url)
        msg = '{0}'.format(e)
        raise Exception(msg)

def NLPTextClassify(_text, _mage_cfg, _time_out):
    pubkey, secret, base_url = r'', r'', r''
    log_record = LogRecord()
    try:
        # 解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        text = param_util.get_classify_text(_text)
        time_out = param_util.get_time_out_param(_time_out)
        # 构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body_for_doc(text)
        start_time = datetime.datetime.now()
        retry_num = 3
        res_data = None
        for i in range(retry_num):  # 重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['text_classify'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:  # 重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        # 简单地后处理网络返回的响应消息
        result = process_text_classify_result(res_data)
        log_record.upload_log(pubkey, secret, 1, 'NLPTextClassify', base_url)
        return result
    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'NLPTextClassify', base_url)
        msg = '{0}'.format(e)
        raise Exception(msg)

def NLPTextExtract(_text, _mage_cfg, _time_out):
    function_name = sys._getframe().f_code.co_name
    print('{0} Enter.'.format(function_name))
    pubkey, secret, base_url = r'', r'', r''
    log_record = LogRecord()
    try:
        # 解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        text = param_util.get_extract_text(_text)
        time_out = param_util.get_time_out_param(_time_out)
        # 构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body_for_doc(text)
        start_time = datetime.datetime.now()
        retry_num = 3
        res_data = None
        for i in range(retry_num):  # 重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['text_extract'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:  # 重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        # 简单地后处理网络返回的响应消息
        result = process_text_extract_result(res_data)
        log_record.upload_log(pubkey, secret, 1, function_name, base_url)
        return result
    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, function_name, base_url)
        msg = '{0}'.format(e)
        raise Exception(msg)

def NLPTextFileExtract(_text_file, _mage_cfg, _time_out):
    try:
        param_util = ParamUtil()
        text_file = param_util.get_text_file_name_param(_text_file)
        try:
            with open(text_file, "r", encoding="utf-8") as f:
                text = f.read()
                if len(text) > 30000:
                    raise Exception(UiBot.GetString("Mage/TextSizeTooLong"))
        except Exception as ex:
            raise Exception(UiBot.GetString("Mage/OpenFileErr") + '{0}'.format(ex))
        return NLPTextExtract(text, _mage_cfg, _time_out)
    except Exception as e:
        msg = '{0}'.format(e)
        raise Exception(msg)

def ImageOCRTemplate(_file_path_name, _mage_cfg, _time_out):
    function_name = sys._getframe().f_code.co_name
    print('{0} Enter.'.format(function_name))
    pubkey, secret, base_url = r'', r'', r''
    log_record = LogRecord()
    try:
        #解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        file_path_name = param_util.get_file_name_param(_file_path_name)
        time_out = param_util.get_time_out_param(_time_out)
        #构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body_for_template(file_path_name)
        start_time = datetime.datetime.now()
        retry_num = 3
        res_data = None
        for i in range(retry_num):#重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['ocr_template'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:#重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        #简单地后处理网络返回的响应消息
        result = process_ocr_template_result(res_data, 1)
        log_record.upload_log(pubkey, secret, 1, function_name, base_url)
        return result
    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, function_name, base_url)
        msg = '{0}'.format(e)
        raise Exception(msg)

def ScreenOCRTemplate(_element, _rect, _mage_cfg, _time_out, _option= default_option):
    function_name = sys._getframe().f_code.co_name
    print('{0} Enter.'.format(function_name))
    shell = None
    file_path_name = None
    err_msg = None
    continue_on_err = False
    result = dict()
    pubkey, secret, base_url = r'', r'', r''
    log_record = LogRecord()
    try:
        # 解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        element = param_util.get_element_param(_element)
        x, y, width, height = param_util.get_rect_param(_rect)
        time_out = param_util.get_time_out_param(_time_out)
        option = param_util.get_option_param(_option)
        delay_before, delay_after = param_util.get_delay_param(option)
        continue_on_err = param_util.get_continue_on_err_param(option)
        active_window = param_util.get_active_window_param(option)

        time_delay(delay_before)
        start_time = datetime.datetime.now()
        shell, file_path_name = screen_shot(element, x, y, width, height, active_window, time_out)
        # 构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body_for_template(file_path_name)
        retry_num = 3
        res_data = None
        for i in range(retry_num):  # 重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['ocr_template'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:  # 重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        # 简单地后处理网络返回的响应消息
        result = process_ocr_template_result(res_data, 1)
        time_delay(delay_after)
        log_record.upload_log(pubkey, secret, 1, function_name, base_url)
    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, function_name, base_url)
        err_msg = str(e)

    if file_path_name != None:
        delete_file(file_path_name)
    if shell != None:
        shell.ToggleDesktop()
    if err_msg != None:
        if continue_on_err == False:
            raise Exception(err_msg)
        else:
            return result
    else:
        return result

def GetTextExtractFieldList(_mage_cfg, _template_name, _time_out):
    try:
        # 解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        template_name = param_util.get_template_name(_template_name)
        time_out = param_util.get_time_out_param(_time_out)
        # 构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body_for_text_extract_version_list()
        start_time = datetime.datetime.now()
        retry_num = 3
        page_size = 200
        for i in range(retry_num):  # 重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['text_extract_query_version_list'], msg_header, msg_body, left_time_out)
                version_hash = get_extract_version_hash_from_net_result(res_data)
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                msg_body1 = mage_client.generate_body_for_text_extract_template_list(version_hash, 1, page_size)
                res_data = mage_client.do_request(url_route_dict['text_extract_query_template_list'], msg_header, msg_body1, left_time_out)
                merge_template_list = list()
                template_list, total_count = get_extract_templates_list_from_net_result(res_data)
                merge_template_list.extend(template_list)
                pg_num = int(total_count / page_size) + 1
                print("total_count:{0}, pg_name:{1}".format(total_count, pg_num))
                for pg_id in range(1, pg_num):
                    left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                    if left_time_out <= 0:
                        i = retry_num - 1
                        raise Exception(UiBot.GetString("Mage/TimeOut"))
                    msg_body1 = mage_client.generate_body_for_text_extract_template_list(version_hash, pg_id + 1, page_size)
                    res_data = mage_client.do_request(url_route_dict['text_extract_query_template_list'], msg_header, msg_body1, left_time_out)
                    template_list, _ = get_extract_templates_list_from_net_result(res_data)
                    merge_template_list.extend(template_list)
                return  get_extract_field_list(merge_template_list, template_name)
            except Exception as e:
                if i == retry_num - 1:  # 重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass
    except Exception as e:
        msg = '{0}'.format(e)
        raise Exception(msg)

def GetOCRTemplateFieldList(_mage_cfg, _template_name, _time_out):
    try:
        # 解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        template_name = param_util.get_template_name(_template_name)
        time_out = param_util.get_time_out_param(_time_out)
        # 构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        page_size = 200
        msg_body = mage_client.generate_body_for_ocr_template_list(1, page_size)
        start_time = datetime.datetime.now()
        retry_num = 3
        for i in range(retry_num):  # 重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['ocr_template_query_template_list'], msg_header, msg_body, left_time_out)

                merge_template_list = list()
                template_list, total_count = get_template_template_list_from_net_result(res_data)
                merge_template_list.extend(template_list)
                pg_num = int(total_count / page_size) + 1
                print("total_count:{0}, pg_name:{1}".format(total_count, pg_num))
                for pg_id in range(1, pg_num):
                    msg_body1 = mage_client.generate_body_for_ocr_template_list(pg_id + 1, page_size)
                    res_data = mage_client.do_request(url_route_dict['ocr_template_query_template_list'], msg_header, msg_body1, left_time_out)
                    template_list, _ = get_template_template_list_from_net_result(res_data)
                    merge_template_list.extend(template_list)
                return get_template_filed_list(merge_template_list, template_name)
            except Exception as e:
                if i == retry_num - 1:  # 重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass
    except Exception as e:
        msg = '{0}'.format(e)
        raise Exception(msg)

def QuerySurplusQuota(_mage_cfg, _time_out):
    try:
        # 解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        time_out = param_util.get_time_out_param(_time_out)
        # 构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body_for_query_recognizer(pubkey, secret)
        start_time = datetime.datetime.now()
        retry_num = 3
        res_data = None
        for i in range(retry_num):  # 重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['listbykey'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:  # 重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        # 简单地后处理网络返回的响应消息
        left_quota = process_query_recognizer_result(res_data)
        return left_quota
    except Exception as e:
        msg = '{0}'.format(e)
        raise Exception(msg)


#### 印章识别 add by CaiCQ on 2021-05-13
def ImageOCRStamp(_file_path_name, _mage_cfg, _time_out):
    pubkey, secret, base_url = r'', r'', r''
    log_record = LogRecord()
    try:
        #解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        file_path_name = param_util.get_file_name_param(_file_path_name)
        time_out = param_util.get_time_out_param(_time_out)
        #构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body(file_path_name)
        start_time = datetime.datetime.now()
        retry_num = 3
        res_data = None
        for i in range(retry_num):#重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['stamp'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:#重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        #简单地后处理网络返回的响应消息
        text_recg_result = process_stamp_result(res_data)
        # log_record.upload_log(pubkey, secret, 1, 'ImageOcrStamp', base_url)
        return text_recg_result
    except Exception as e:
        # log_record.upload_log(pubkey, secret, 0, 'ImageOcrStamp', base_url)
        msg = '{0}'.format(e)
        raise Exception(msg)

def ScreenOCRStamp(_element, _rect, _mage_cfg, _time_out, _option= default_option):
    shell = None
    file_path_name = None
    err_msg = None
    continue_on_err = False
    text_recg_result = dict()
    pubkey, secret, base_url = r'', r'', r''
    log_record = LogRecord()
    try:
        # 解析并校验输入参数的合法性
        param_util = ParamUtil()
        pubkey, secret, base_url = param_util.get_mage_access_param(_mage_cfg)
        element = param_util.get_element_param(_element)
        x, y, width, height = param_util.get_rect_param(_rect)
        time_out = param_util.get_time_out_param(_time_out)
        option = param_util.get_option_param(_option)
        delay_before, delay_after = param_util.get_delay_param(option)
        continue_on_err = param_util.get_continue_on_err_param(option)
        active_window = param_util.get_active_window_param(option)

        time_delay(delay_before)
        start_time = datetime.datetime.now()
        shell, file_path_name = screen_shot(element, x, y, width, height, active_window, time_out)
        # 构造并发送网络请求
        mage_client = MageClient(base_url)
        msg_header = mage_client.generate_header(pubkey, secret)
        msg_body = mage_client.generate_body(file_path_name)
        retry_num = 3
        res_data = None
        for i in range(retry_num):  # 重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['stamp'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:  # 重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        # 简单地后处理网络返回的响应消息
        text_recg_result = process_stamp_result(res_data)
        time_delay(delay_after)
        log_record.upload_log(pubkey, secret, 1, 'ScreenOCRStamp', base_url)
    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'ScreenOCRStamp', base_url)
        err_msg = str(e)

    if file_path_name != None:
        delete_file(file_path_name)
    if shell != None:
        shell.ToggleDesktop()
    if err_msg != None:
        if continue_on_err == False:
            raise Exception(err_msg)
        else:
            return text_recg_result
    else:
        return text_recg_result



#################################################################
#Created on 2020年8月1日
#@author: CaiCQ
#################################################################
class _ParamType:
    OCR_RESULT = 1
    SELECTION = 2

def _SafeGetValue(jsonSource, key, paramType = _ParamType.OCR_RESULT):
    if key not in jsonSource:
        if paramType == _ParamType.OCR_RESULT:
            raise Exception(UiBot.GetString("Mage/OcrResultNoKeyFound") % key)
        elif paramType == _ParamType.SELECTION:
            raise Exception(UiBot.GetString("Mage/SelectionParamNoKeyFound"))
    return jsonSource[key]

# 从通用文本识别结果中提取信息
def __GetValueFromTextResult(ocrResult, valueType):
    if type(ocrResult) is list:
        raise Exception(UiBot.GetString("Mage/OcrResultIsAnArray"))
    if 'ai_function' not in ocrResult or ocrResult['ai_function'] != 'ocr_text':
        raise Exception(UiBot.GetString("Mage/NotATextOcrResult"))

    if valueType == 'sentence_text':
        itemsList = _SafeGetValue(ocrResult, 'items')
        if not itemsList:
            return ""
        sentenceList = list(map(lambda item: item['content'] if type(item) is dict else "" , itemsList))
        return sentenceList
    structContent = _SafeGetValue(ocrResult, 'struct_content')
    if not structContent:
        return ""
    if valueType == 'all_text_without_enter':
        pageList = _SafeGetValue(structContent, 'page')
        if not pageList: 
            return ""
        contentList = map(lambda p: p['content'] if type(p) is dict else "" , pageList)
        content = "".join(contentList)
        return content
    elif valueType == 'all_text_with_enter':
        rowList = _SafeGetValue(structContent, 'row')
        if not rowList:
            return ""
        contentList = map(lambda row: row['content'] if type(row) is dict else "" , rowList)
        return '\n'.join(contentList)
    elif valueType == 'paragraph_text':
        paragraphList = _SafeGetValue(structContent, 'paragraph')
        if not paragraphList:
            return ""
        contentList = list(map(lambda p: p['content'] if type(p) is dict else "" , paragraphList))
        return contentList
    elif valueType == 'row_text':
        rowList = _SafeGetValue(structContent, 'row')
        if not rowList:
            return ""
        contentList = list(map(lambda row: row['content'] if type(row) is dict else "" , rowList))
        return contentList

    raise Exception(UiBot.GetString("Mage/UnsupportExtractPropertyFromTextOcrResult") % (valueType,))
#获取全部文本
def ExtractAllText(ocrResult, enter_status):
    param_util = ParamUtil()
    enter_status = param_util.get_enter_status(enter_status)
    if enter_status == True:
        valueType = "all_text_with_enter"
    else:
        valueType = "all_text_without_enter"
    return __GetValueFromTextResult(ocrResult, valueType)
#获取段落文本
def ExtractParagraphText(ocrResult):
    return __GetValueFromTextResult(ocrResult, "paragraph_text")
#获取行文本
def ExtractLineText(ocrResult):
    return __GetValueFromTextResult(ocrResult, "row_text")
#获取词句文本
def ExtractSentenceText(ocrResult):
    return __GetValueFromTextResult(ocrResult, "sentence_text")

# 从卡证识别结果中提取信息
def __GetValueFromCardResult(ocrResult, cardType, cardKey, breakWithoutFinalKey = False):
    if type(ocrResult) is list:
        raise Exception(UiBot.GetString("Mage/OcrResultIsAnArray"))
    if 'ai_function' not in ocrResult or ocrResult['ai_function'] != 'ocr_card':
        raise Exception(UiBot.GetString("Mage/NotACardOcrResult"))

    cardResult = _SafeGetValue(ocrResult, 'result')
    typeKey = _SafeGetValue(cardResult, 'type_key')
    if cardType == 'card_type':
        return typeKey

    if cardType != typeKey:
        raise Exception(UiBot.GetString("Mage/CardInvoiceTypeNotMatch") % (cardType,))
    itemsList = _SafeGetValue(cardResult, 'items')
    cardInfo = list(filter(lambda item: cardKey == item['key'] if type(item) is dict else False, itemsList))
    if len(cardInfo) == 0:
        if breakWithoutFinalKey:
            raise Exception(UiBot.GetString("Mage/UnsupportExtractPropertyFromCardOcrResult") % (cardKey,))
        else:
            return ""

    return cardInfo[0]['value']
#获取卡证类型
def ExtractCardType(ocrResult):
    return __GetValueFromCardResult(ocrResult, 'card_type', '')
#获取卡证内容
def ExtractCardInfo(ocrResult, cardType, cardKey):
    return __GetValueFromCardResult(ocrResult, cardType, cardKey)

# 从票据结果中提取信息
def __GetValueFromInvoiceResult(ocrResult, billsType, billsKey, breakWithoutFinalKey = False):
    if type(ocrResult) is list:
        raise Exception(UiBot.GetString("Mage/OcrResultIsAnArray"))
    if 'ai_function' not in ocrResult or ocrResult['ai_function'] != 'ocr_invoice':
        raise Exception(UiBot.GetString("Mage/NotAnInvoiceOcrResult"))

    typeKey = _SafeGetValue(ocrResult, 'type_key')
    if billsType == 'bills_type':
        return typeKey

    if billsType != typeKey:
        raise Exception(UiBot.GetString("Mage/CardInvoiceTypeNotMatch") % (billsType,))
    itemsList = _SafeGetValue(ocrResult, 'items')
    invoiceInfo = list(filter(lambda item: billsKey == item['key'] if type(item) is dict else False, itemsList))
    if len(invoiceInfo) == 0:
        if breakWithoutFinalKey:
            raise Exception(UiBot.GetString("Mage/UnsupportExtractPropertyFromInvoiceOcrResult")%(billsKey,))
        else:
            return ""

    return invoiceInfo[0]['value']

#获取票据类型
def ExtractInvoiceType(ocrResult):
    return __GetValueFromInvoiceResult(ocrResult, 'bills_type', '')
#获取票据内容
def ExtractInvoiceInfo(ocrResult, invoiceType, invoiceKey):
    return __GetValueFromInvoiceResult(ocrResult, invoiceType, invoiceKey)

#提取信息提取命令的模板名称
def ExtractTextExtractName(textExtractResult):
    if type(textExtractResult) is list:
        raise Exception(UiBot.GetString("Mage/OcrResultIsAnArray"))
    if 'ai_function' not in textExtractResult or textExtractResult['ai_function'] != 'nlp_text_extract':
        raise Exception(UiBot.GetString("Mage/NotAnTextExtractResult"))
    templateName = _SafeGetValue(textExtractResult, 'name')
    return templateName

#提取信息提取命令的字段内容
def ExtractTextExtractInfo(textExtractResult, mageCfg, templateName, fieldName, _updateTime, _index, bIsStdValue):
    if type(textExtractResult) is list:
        raise Exception(UiBot.GetString("Mage/OcrResultIsAnArray"))
    if 'ai_function' not in textExtractResult or textExtractResult['ai_function'] != 'nlp_text_extract':
        raise Exception(UiBot.GetString("Mage/NotAnTextExtractResult"))
    paramUtil = ParamUtil()
    index = paramUtil.get_index_param(_index)
    updateTimeDesign = paramUtil.get_update_time_param(_updateTime)
    updateTimeRunning = _SafeGetValue(textExtractResult, 'update_time')
    check_update_time_is_conflict(sys._getframe().f_code.co_name, sys._getframe().f_lineno, updateTimeDesign, updateTimeRunning)
    _templateName = _SafeGetValue(textExtractResult, 'name')
    if _templateName != templateName:
        raise Exception(UiBot.GetString("Mage/TemplateNameNotMatch") % (_templateName, templateName))
    itemsList = _SafeGetValue(textExtractResult, 'fields')
    fieldInfoList = list(filter(lambda item: fieldName == item['name'] if type(item) is dict else False, itemsList))
    if len(fieldInfoList) == 0:
        return ""
    # 检测index参数是否溢出
    if len(fieldInfoList) <= index:
        raise Exception(UiBot.GetString("Mage/TextExtracIndexOutOfRange").format(len(fieldInfoList), len(fieldInfoList)))
    fieldInfo = fieldInfoList[index]
    bIsStdValue = paramUtil.get_is_std_value(bIsStdValue)
    if bIsStdValue:
        return fieldInfo["std_value"]
    else:
        return fieldInfo["value"]

# 提取自定义模板识别命令的模板名称
def ExtractOCRTemplateName(ocrTemplateResult):
    if type(ocrTemplateResult) is list:
        raise Exception(UiBot.GetString("Mage/OcrResultIsAnArray"))
    if 'ai_function' not in ocrTemplateResult or ocrTemplateResult['ai_function'] != 'ocr_template':
        raise Exception(UiBot.GetString("Mage/NotAnTemplateResult"))
    templateName = _SafeGetValue(ocrTemplateResult, 'template_name')
    return templateName

# 提取自定义模板识别命令的字段内容
def ExtractOCRTemplateInfo(ocrTemplateResult, mageCfg, templateName, fieldName, _updateTime):
    if type(ocrTemplateResult) is list:
        raise Exception(UiBot.GetString("Mage/OcrResultIsAnArray"))
    if 'ai_function' not in ocrTemplateResult or ocrTemplateResult['ai_function'] != 'ocr_template':
        raise Exception(UiBot.GetString("Mage/NotAnTemplateResult"))
    paramUtil = ParamUtil()
    updateTimeDesign = paramUtil.get_update_time_param(_updateTime)
    updateTimeRunning = _SafeGetValue(ocrTemplateResult, 'update_time')
    check_update_time_is_conflict(sys._getframe().f_code.co_name, sys._getframe().f_lineno, updateTimeDesign, updateTimeRunning)
    _templateName = _SafeGetValue(ocrTemplateResult, 'template_name')
    if _templateName != templateName:
        raise Exception(UiBot.GetString("Mage/TemplateNameNotMatch") % (_templateName, templateName))
    itemsList = _SafeGetValue(ocrTemplateResult, 'results')
    fieldInfoList = list(filter(lambda item: fieldName == item['field_name'] if type(item) is dict else False, itemsList))
    if len(fieldInfoList) == 0:
        return ""
    return fieldInfoList[0]['results']
#提取地址信息
def ExtractAddress(nlpResult, addrType):
    if type(nlpResult) is list:
        raise Exception(UiBot.GetString("Mage/OcrResultIsAnArray"))
    if 'ai_function' not in nlpResult or nlpResult['ai_function'] != 'nlp_addr_std':
        raise Exception(UiBot.GetString("Mage/NotAAddressStdResult"))
    if addrType == "whole_address": #完整地址
        #省+市+区县+街道+详细地址
        return  _SafeGetValue(nlpResult, 'province') + _SafeGetValue(nlpResult, 'city') + \
                _SafeGetValue(nlpResult, 'district') + _SafeGetValue(nlpResult, 'subdistrict') + \
                _SafeGetValue(nlpResult, 'address')
    elif addrType == "province":    #省
        return _SafeGetValue(nlpResult, 'province')
    elif addrType == "city":    #市
        return _SafeGetValue(nlpResult, 'city')
    elif addrType == "district":    #区县
        return _SafeGetValue(nlpResult, 'district')
    elif addrType == "subdistrict":    #街道
        return _SafeGetValue(nlpResult, 'subdistrict')
    elif addrType == "address":    #详细地址
        return _SafeGetValue(nlpResult, 'address')
    elif addrType == "poi_name":    #POI名称
        return _SafeGetValue(nlpResult, 'poi_name')
    else:
        raise Exception(UiBot.GetString("Mage/ExtractAddressTypeErr"))

#获取排名结果
def ExtractTextClassifyTopN(nlpResult, scoreThrd, topN):
    #分本分类的输入参数必须是数组
    if type(nlpResult) is not list:
        raise Exception(UiBot.GetString("Mage/TextClassifyInputErr"))
    param_util = ParamUtil()
    scoreThrd = param_util.get_score_thrd_param(scoreThrd)
    topN = param_util.get_top_n_param(topN)
    if len(nlpResult) == 0:
        return list()
    if 'ai_function' not in nlpResult[0] or nlpResult[0]['ai_function'] != 'nlp_text_classify':
        raise Exception(UiBot.GetString("Mage/NotATextClassifyResult"))
    #排序、过滤、取排名前n名
    nlpResult.sort(key=lambda x: x['score'], reverse=True)
    tempArr = list(filter(lambda item: item['score'] >= scoreThrd, nlpResult))
    resultArr = [x['class_label'] for x in tempArr]
    return resultArr[:topN]

#表格信息提取类，封装针对表格的多类信息提取操作
class TableExtractUtil:
    class Local:
        def __init__(self):
            self.center_x = 0
            self.center_y = 0

    class TableInfo:
        class Merge:
            def __init__(self):
                self.start_row = 0
                self.start_col = 0
                self.end_row = 0
                self.end_col = 0

        def __init__(self):
            self.merge_info = list()
            self.row_info = list()

        def add_merge_info(self, start_row, start_col, end_row, end_col):
            merge = self.Merge()
            merge.start_row = start_row
            merge.start_col = start_col
            merge.end_row = end_row
            merge.end_col = end_col
            self.merge_info.append(merge)

        def add_row_data(self, row_data):
            self.row_info.append(row_data)

    class OutTableText:
        def __init__(self):
            self.content = ''

        def set_text_content(self, _content):
            self.content = _content

    def __init__(self):
        self.tables = list()
        self.texts = list()
        self.order_info = list()

    def _get_center_pt(self, positions_list):
        positions_x = [pt['x'] for pt in positions_list]
        positions_y = [pt['y'] for pt in positions_list]
        center_x = int((max(positions_x) + min(positions_x)) * 0.5)
        center_y = int((max(positions_y) + min(positions_y)) * 0.5)
        return center_x, center_y

    def _get_single_row(self, cellList, row):
        #按行做过滤处理，把跨列的单元格做处理
        cells = filter(lambda cell: (row in range(cell['start_row'], cell['end_row'] + 1)) if type(cell) is dict and \
                       'start_row' in cell and 'end_row' in cell else False, cellList)
        cells = sorted(cells, key=lambda cell:cell["start_col"])    #根据列号排序，不然可能是错位的
        contents = list(map(lambda cell: cell['content'] if type(cell) is dict and 'content' in cell and row == cell['start_row'] else '', cells))
        counts = list(map(lambda cell: cell['end_col'] - cell['start_col'] + 1, cells))  # 取一行得看有没有跨列的

        rowContents = []
        for i in range(len(counts)):
            for j in range(counts[i]):
                cell_content = contents[i] if j == 0 else ''    #合并的单元格以空字符占位
                rowContents.append(cell_content)


        return rowContents

    def get_local_marge(self, center_x, center_y, table_or_text, index):
        local_marge = dict()
        local_marge['center_x'] = center_x
        local_marge['center_y'] = center_y
        local_marge['table_or_text'] = table_or_text
        local_marge['index'] = index
        return local_marge

    def get_order_info(self):
        self.order_info.sort(key=lambda x: x['center_y'], reverse=False)
        return self.order_info

    def get_tables(self):
        return self.tables

    def get_texts(self):
        return self.texts

    def parse_table_result(self, json_table_result):
        # step1: 解析非表格的文字区域
        json_arr_text = _SafeGetValue(json_table_result, 'items')
        index = 0
        for text_item in json_arr_text:
            content = _SafeGetValue(text_item, 'content')
            if content == '':
                continue
            page_number = _SafeGetValue(text_item, 'page_number')
            position_list = _SafeGetValue(text_item, 'positions')
            center_x, center_y = self._get_center_pt(position_list)
            #针对pdf的情况，为了保证后面的页的坐标大于前面页的坐标，这里做个特殊处理
            center_y += (page_number - 1) * 1000000

            out_table_text = TableExtractUtil.OutTableText()
            out_table_text.set_text_content(content)
            self.texts.append(out_table_text)

            local_marge = self.get_local_marge(center_x, center_y, 0, index)
            self.order_info.append(local_marge)
            index += 1

        # step2: 解析表格区域
        json_arr_table = _SafeGetValue(json_table_result, 'tables')
        index = 0
        for table_item in json_arr_table:
            one_table_info = TableExtractUtil.TableInfo()
            cell_list = _SafeGetValue(table_item, 'cells')
            center_x_list = list()
            center_y_list = list()
            for cell in cell_list:
                start_row = _SafeGetValue(cell, 'start_row')
                start_col = _SafeGetValue(cell, 'start_col')
                end_row = _SafeGetValue(cell, 'end_row')
                end_col = _SafeGetValue(cell, 'end_col')
                if start_row != end_row or start_col != end_col:
                    one_table_info.add_merge_info(start_row, start_col, end_row, end_col)
                center_x, center_y = self._get_center_pt(_SafeGetValue(cell, 'positions'))
                center_x_list.append(center_x)
                center_y_list.append(center_y)

            center_x = int((max(center_x_list) + min(center_x_list)) * 0.5)
            center_y = int((max(center_y_list) + min(center_y_list)) * 0.5)
            # 针对pdf的情况，为了保证后面的页的坐标大于前面页的坐标，这里做个特殊处理
            page_number = _SafeGetValue(table_item, 'page_number')
            center_y += (page_number - 1) * 1000000

            row_count = _SafeGetValue(table_item, 'row')
            for row_id in range(row_count):
                row_data = self._get_single_row(cell_list, row_id)
                one_table_info.add_row_data(row_data)
            self.tables.append(one_table_info)

            local_marge = self.get_local_marge(center_x, center_y, 1, index)
            self.order_info.append(local_marge)
            index += 1

def ExtractOutsideTableText(ocrResult):
    if 'ai_function' not in ocrResult or ocrResult['ai_function'] != 'ocr_table':
        raise Exception(UiBot.GetString("Mage/NotATableOcrResult"))
    table_extract_util = TableExtractUtil()
    table_extract_util.parse_table_result(ocrResult)
    text_list = list()
    for text_item in table_extract_util.texts:
        text_list.append(text_item.content)
    return text_list

def ExtractTablesNum(ocrResult):
    if 'ai_function' not in ocrResult or ocrResult['ai_function'] != 'ocr_table':
        raise Exception(UiBot.GetString("Mage/NotATableOcrResult"))
    table_extract_util = TableExtractUtil()
    table_extract_util.parse_table_result(ocrResult)
    return len(table_extract_util.tables)

def ExtractAllTables(ocrResult):
    if 'ai_function' not in ocrResult or ocrResult['ai_function'] != 'ocr_table':
        raise Exception(UiBot.GetString("Mage/NotATableOcrResult"))
    table_extract_util = TableExtractUtil()
    table_extract_util.parse_table_result(ocrResult)
    table_list = list()
    for table_item in table_extract_util.tables:
        table_list.append(table_item.row_info)
    return table_list

def ExtractSingleTable(ocrResult, tableId):
    if 'ai_function' not in ocrResult or ocrResult['ai_function'] != 'ocr_table':
        raise Exception(UiBot.GetString("Mage/NotATableOcrResult"))
    param_util = ParamUtil()
    table_id = param_util.get_table_id_param(tableId)
    table_extract_util = TableExtractUtil()
    table_extract_util.parse_table_result(ocrResult)
    table_num = len(table_extract_util.tables)
    if table_id >= table_num:
        raise Exception(UiBot.GetString("Mage/TableIdOutOfRange").format(table_id, table_num))

    table_item = table_extract_util.tables[table_id]
    return table_item.row_info

def ExtractTableRegion(tableObj, startRow, startCol, endRow, endCol):
    param_util = ParamUtil()
    table_obj = param_util.get_table_obj_param(tableObj)
    start_row, start_col, end_row, end_col = param_util.get_table_range_param(startRow, startCol, endRow, endCol)
    np_table_obj = np.array(table_obj)
    row_num, col_num = np_table_obj.shape
    if start_row > row_num or end_row > row_num or start_col > col_num or end_col > col_num:
        raise Exception(UiBot.GetString("Mage/RowOrColumnExceeded"))
    np_range = np_table_obj[start_row - 1: end_row, start_col - 1:end_col]
    list_range = np_range.tolist()
    return list_range

def ExtractSingleTableRowNum(tableObj):
    param_util = ParamUtil()
    table_obj = param_util.get_table_obj_param(tableObj)
    np_table_obj = np.array(table_obj)
    row_num, col_num = np_table_obj.shape
    return row_num

def ExtractSingleTableColNum(tableObj):
    param_util = ParamUtil()
    table_obj = param_util.get_table_obj_param(tableObj)
    np_table_obj = np.array(table_obj)
    row_num, col_num = np_table_obj.shape
    return col_num

def ExtractSingleTableRow(tableObj, rowId):
    param_util = ParamUtil()
    table_obj = param_util.get_table_obj_param(tableObj)
    row_id = param_util.get_row_and_col_param(rowId)
    np_table_obj = np.array(table_obj)
    row_num, col_num = np_table_obj.shape
    if row_id > row_num:
        raise Exception(UiBot.GetString("Mage/RowOrColumnExceeded"))
    np_one_row_data = np_table_obj[row_id - 1, :]
    one_row_data = np_one_row_data.tolist()
    return one_row_data

def ExtractSingleTableCol(tableObj, colId):
    param_util = ParamUtil()
    table_obj = param_util.get_table_obj_param(tableObj)
    col_id = param_util.get_row_and_col_param(colId)
    np_table_obj = np.array(table_obj)
    row_num, col_num = np_table_obj.shape
    if col_id > col_num:
        raise Exception(UiBot.GetString("Mage/RowOrColumnExceeded"))
    np_one_col_data = np_table_obj[:, col_id - 1]
    one_col_data = np_one_col_data.tolist()
    return one_col_data

def ExtractSingleTableCell(tableObj, rowId, colId):
    param_util = ParamUtil()
    table_obj = param_util.get_table_obj_param(tableObj)
    row_id = param_util.get_row_and_col_param(rowId)
    col_id = param_util.get_row_and_col_param(colId)
    np_table_obj = np.array(table_obj)
    row_num, col_num = np_table_obj.shape
    if col_id > col_num or row_id > row_num:
        raise Exception(UiBot.GetString("Mage/RowOrColumnExceeded"))
    np_cell_data = np_table_obj[row_id - 1, col_id - 1]
    cell_data = np_cell_data.tolist()
    return cell_data

def ExtractTablesToExcel(ocrResult, _is_filter_text, _excel_path_name, _appType=''):
    def _mk_tmpname(filepath):
        dirname = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        while True:
            tmppath = os.path.join(dirname, str(uuid.uuid4())[:8] + '_' + filename)
            if not os.path.exists(tmppath):
                return tmppath

    excel_obj = None
    isSave = True
    tmp_path = None
    try:
        if 'ai_function' not in ocrResult or ocrResult['ai_function'] != 'ocr_table':
            raise Exception(UiBot.GetString("Mage/NotATableOcrResult"))
        param_util = ParamUtil()
        is_filter_text = param_util.get_filter_text_status(_is_filter_text)
        table_extract_util = TableExtractUtil()
        table_extract_util.parse_table_result(ocrResult)
        order_info = table_extract_util.get_order_info()
        tables_info = table_extract_util.get_tables()
        text_info = table_extract_util.get_texts()
        if is_filter_text and len(tables_info) <= 0:#只提取表格
            raise Exception(UiBot.GetString("Mage/CannotExtractContentFromTableOcrResult"))
        if not is_filter_text and len(tables_info) <= 0 and len(text_info) <= 0:#提取全部信息
            raise Exception(UiBot.GetString("Mage/CannotExtractContentFromTableOcrResult"))
        if os.path.exists(_excel_path_name) and not os.access(_excel_path_name, os.W_OK):
            raise Exception(UiBot.GetString("Mage/PathNoWritePerm"))
        if not os.access(os.path.dirname(_excel_path_name), os.W_OK):
            raise Exception(UiBot.GetString("Mage/PathNoWritePerm"))
        
        tmp_path = _mk_tmpname(_excel_path_name) if os.path.exists(_excel_path_name) else _excel_path_name
        # 其它Excel相关参数的校验统一复用Excel模块的参数校验方式
        # OpenExcel(path=None,visible=True,appType="",pwd="",writePwd="")
        if _system == 'windows':
            excel_obj = Excel.OpenExcel(tmp_path, False, _appType, "", "")
        else:
            excel_obj = Excel.OpenExcel(tmp_path, {'Timeout': 120000})
        max_col_num = 0
        for table_obj in tables_info:
            np_table_obj = np.array(table_obj.row_info)
            row_num, col_num = np_table_obj.shape
            if max_col_num < col_num:
                max_col_num = col_num

        def get_start_cell(row, col):
            return [row, col]
        def get_region(start_row, start_col, end_row, end_col):
            return [[start_row, start_col], [end_row, end_col]]
        def get_sheet(sheet_id):
            return 'Sheet' + str(sheet_id)

        # 由于不同语言的系统（如繁体）默认的sheet页的名称不一样，这里需要预处理成Sheet1的命名方式
        all_sheets_name = Excel.GetSheetsName(excel_obj)
        if len(all_sheets_name) > 0:
            default_sheet_name = all_sheets_name[0]
            if default_sheet_name != get_sheet(1):
                Excel.SheetRename(excel_obj,default_sheet_name,get_sheet(1),True)
        current_row = 1
        current_col = 1
        sheet_id = 1
        for order_item in order_info:
            table_or_text = order_item.get('table_or_text')
            index = order_item.get('index')
            if table_or_text == 0:
                # 非表格文本
                if is_filter_text:
                    continue
                content = text_info[index].content
                # 将非表格文本内容写入单元格中，并做单元格合并
                # MergeRange(objWB,sheet,cell,bOption=True,isSave=False)
                region = get_region(current_row, current_col, current_row, current_col + max_col_num)
                Excel.MergeRange(excel_obj, get_sheet(sheet_id), region, True, True)

                # WriteCell(objWB=None,sheet=0,cell="A1",text=None,isSave=False)
                Excel.WriteCell(excel_obj, get_sheet(sheet_id), get_start_cell(current_row, current_col), "'" + str(content), True)
                current_row = current_row + 2
            else:
                # 表格
                if sheet_id != 1:
                    # CreateSheet(objWB,sheet="newSheet",strWhere="after",isSave=False)
                    Excel.CreateSheet(excel_obj, get_sheet(sheet_id), 'after', True)
                table_obj = tables_info[index].row_info  # 表格的数据，二维数组
                merge_obj = tables_info[index].merge_info  # 单元格合并信息，一维数组
                np_table_obj = np.array(table_obj)
                row_num, col_num = np_table_obj.shape
                # 将表格数据写入Excel区域中，并合并对应的单元格
                for merge_item in merge_obj:
                    start_row = merge_item.start_row + current_row
                    start_col = merge_item.start_col + current_col
                    end_row = merge_item.end_row + current_row
                    end_col = merge_item.end_col + current_col
                    Excel.MergeRange(excel_obj, get_sheet(sheet_id), get_region(start_row, start_col, end_row, end_col), True, True)

                # WriteRange(objWB=None,sheet=0,startCell="A1",arrData=[],isSave=False)
                table_obj_conv = list(map(lambda row: list(map(lambda cell: "'" + str(cell), row)), table_obj))
                #print(table_obj_conv)
                Excel.WriteRange(excel_obj, get_sheet(sheet_id), get_start_cell(current_row, 1), table_obj_conv, True)
                if is_filter_text:
                    sheet_id += 1
                else:
                    current_row = current_row + row_num + 1

        if tmp_path != _excel_path_name:
            shutil.copyfile(tmp_path, _excel_path_name)
    except Exception as e:
        #import traceback
        #traceback.print_exc()
        isSave = False
        msg = '{0}'.format(e)
        raise Exception(msg)
    finally:
        if tmp_path and tmp_path != _excel_path_name and os.path.exists(tmp_path):
            os.remove(tmp_path)
        #CloseExcel(wb,isSave=True)
        if excel_obj != None:
            if _system == 'windows':
                Excel.CloseExcel(excel_obj, isSave)
            else:
                Excel.CloseExcel(excel_obj, isSave, True)


def ExtractStampInfo(ocrResult, field):
    if not isinstance(ocrResult, dict):
        raise Exception(UiBot.GetString('Mage/NotAStampOcrResult'))
    if ocrResult.get('ai_function', '') != 'ocr_stamp':
        raise Exception(UiBot.GetString('Mage/NotAStampOcrResult'))

    print('checked ocr result')
    if 'stamps' not in ocrResult or not ocrResult['stamps']:
        print('no stamp info')
        raise Exception(UiBot.GetString('Mage/NoStampsInfo'))
    print('got stamp info')
    stampList = ocrResult['stamps']
    array_result = list()
    for stamp in stampList:
        value = _SafeGetValue(stamp, field)
        array_result.append(value)
    return array_result

# <<<<<<< End of Extract Functions <<<<<<<<<

# -----------> by caichengqiang on 2021-04-30 --------

_default_ocr_text_option = {
    "bContinueOnError":False,
    "iDelayAfter": 300,
    "iDelayBefore": 200,
    "sCursorPosition": "Center",
    "iCursorOffsetX": 0,
    "iCursorOffsetY": 0,
    "sKeyModifiers": [],
    "sSimulate": "simulate"
}

def _find_element(_element, _timeout):
    '''
    查找元素返回元素
    '''
    element = UiBot.InvokeRobotCore(0, 'FindAndActiveElement', [_element, _timeout])
    if element == None or element <= 0:
        raise Exception(UiBot.GetString('Mage/ElementNotFound'))

    return element

def _get_element_rect(_element, _timeout, _rect):
    '''
    查找元素返回选中区的矩形(x,y,width,height)
    '''
    element = _find_element(_element, _timeout)
    element_rect_sr = UiBot.InvokeRobotCore(element, 'UiElementGetRect', ['screen', ''])
    try:
        element_rect = json.loads(element_rect_sr)
    except:
        raise Exception(UiBot.GetString('Mage/ElementRectParseError'))

    if 'x' not in element_rect or \
       'y' not in element_rect or \
       'width' not in element_rect or \
       'height' not in element_rect or \
       element_rect['x'] < 0 or \
       element_rect['y'] < 0 or \
       element_rect['width'] <= 0 or \
       element_rect['height'] <= 0:
       raise Exception(UiBot.GetString('Mage/InvalidElementRect'))

    selection_rect = dict()
    selection_rect['x'] = int(element_rect['x']) + int(_rect['x'])
    selection_rect['y'] = int(element_rect['y']) + int(_rect['y'])
    selection_rect['width'] = int(_rect['width']) if int(_rect['width']) > 0 else int(element_rect['width'])
    selection_rect['height'] = int(_rect['height']) if int(_rect['height']) > 0 else int(element_rect['height'])
    
    return (element_rect, selection_rect)
    
def _transform_option(option, x, y):
    new_option = dict()
    for key in option.keys():
        new_option[key] = option[key]
    
    new_option['sCursorPosition'] = 'TopLeft'
    new_option['iCursorOffsetX'] = int(x)
    new_option['iCursorOffsetY'] = int(y)
    return new_option

def _Find(_element, _rect, _mage_cfg, _text, _rule, _occurrence, _timeout, _option):
    '''
    通过目标元素查找元素，返回元素和文字所在的區域
    '''
    param_util = ParamUtil()
    text = param_util.get_text_param(_text) 
    rule = param_util.get_rule_param(_rule) 
    occurrence = param_util.get_occurrence_param(_occurrence) 
    option = param_util.get_option_param(_option)
    continue_on_err = param_util.get_continue_on_err_param(option)

    found = False
    text_occurrence = 0
    x, y, width, height = 0, 0, 0, 0
    ocr_text_option = {"bContinueOnError":continue_on_err,
                  "iDelayAfter":0,
                  "iDelayBefore":0,
                  "bSetForeground":True}
    text_result = ScreenOCRText(_element, _rect, _mage_cfg, _timeout, ocr_text_option, True)
    sentence_list = ExtractSentenceText(text_result)
    i = 0
    if rule == 'equal':
        for sentence in sentence_list:
            if text == sentence:
                text_occurrence += 1
                if text_occurrence == occurrence:
                    found = True
                    x = text_result['items'][i]['char_positions'][0]['positions'][0]['x'] # left
                    y = text_result['items'][i]['char_positions'][0]['positions'][0]['y'] # top
                    width = text_result['items'][i]['char_positions'][len(text)-1]['positions'][2]['x'] - x # right
                    height = text_result['items'][i]['char_positions'][len(text)-1]['positions'][2]['y'] - y # bottom
                    break
            i += 1
    elif rule == 'instr':
        for sentence in sentence_list:
            if text in sentence:
                text_occurrence += 1
                if text_occurrence == occurrence:
                    found = True
                    start_char_pos = sentence.index(text)
                    end_char_pos = start_char_pos + len(text) - 1
                    x = text_result['items'][i]['char_positions'][start_char_pos]['positions'][0]['x'] # left
                    y = text_result['items'][i]['char_positions'][start_char_pos]['positions'][0]['y'] # top
                    width = text_result['items'][i]['char_positions'][end_char_pos]['positions'][2]['x'] - x # right
                    height = text_result['items'][i]['char_positions'][end_char_pos]['positions'][2]['y'] - y # bottom
                    break
            i += 1
    elif rule == 'regex':
        pattern = re.compile(text)
        for sentence in sentence_list:
            result = pattern.findall(sentence)
            text_occurrence += len(result)
            if text_occurrence >= occurrence:
                found = True
                text_occurrence -= len(result)
                start_char_pos = 0
                for matching_text in result:
                    start_char_pos = sentence.index(matching_text, start_char_pos)
                    text_occurrence += 1
                    if text_occurrence == occurrence:
                        end_char_pos = start_char_pos + len(matching_text) - 1
                        x = text_result['items'][i]['char_positions'][start_char_pos]['positions'][0]['x'] # left
                        y = text_result['items'][i]['char_positions'][start_char_pos]['positions'][0]['y'] # top
                        width = text_result['items'][i]['char_positions'][end_char_pos]['positions'][2]['x'] - x # right
                        height = text_result['items'][i]['char_positions'][end_char_pos]['positions'][2]['y'] - y # bottom
                        break
                break
            i += 1
    if not found:
        raise Exception(UiBot.GetString('Mage/ClickTextNotFound').format(text))

    UiBot.PushContext()
    element_rect, selection_rect = _get_element_rect(_element, _timeout, _rect)
    UiBot.PopContext()
    text_rect = dict()
    x += selection_rect['x']
    y += selection_rect['y']
    text_rect['x'] = x
    text_rect['y'] = y
    text_rect['width'] = width
    text_rect['height'] = height

    return (element_rect, text_rect)

def Find(element, rect, mage_cfg, text, rule, occurrence, timeout, _option = _default_ocr_text_option):
    param_util = ParamUtil()
    option = param_util.get_option_param(_option)
    continue_on_err = param_util.get_continue_on_err_param(option)
    delay_before, delay_after = param_util.get_delay_param(option)
    point = dict()
    try:
        time_delay(delay_before)
        _, rect = _Find(element, rect, mage_cfg, text, rule, occurrence, timeout, option)
        time_delay(delay_after)
        point['x'] = rect['x']
        point['y'] = rect['y']
    except Exception as e:
        if not continue_on_err:
            raise e
        point['x'] = 0
        point['y'] = 0
    return point

def Click(_element, _rect, _mage_cfg, _text, _rule, _occurrence, _button, _click_type, _timeout, _option = _default_ocr_text_option):
    param_util = ParamUtil()
    button = param_util.get_button_param(_button) 
    click_type = param_util.get_click_type_param(_click_type) 
    option = param_util.get_option_param(_option)
    continue_on_err = param_util.get_continue_on_err_param(option)
    try:
        delay_before, delay_after = param_util.get_delay_param(option)
        cursor_postion = param_util.get_cursor_postion_param(option)
        x_offset = param_util.get_x_offset_param(option)
        y_offset = param_util.get_y_offset_param(option)

        time_delay(delay_before)
        element_rect, text_rect = _Find(_element, _rect, _mage_cfg, _text, _rule, _occurrence, _timeout, option)
        x = text_rect['x']
        y = text_rect['y']
        width = text_rect['width']
        height = text_rect['height']

        # calculate relative x,y for MouseAction
        relative_element_x, relative_element_y = 0, 0
        if cursor_postion == 'Center':
            relative_element_x = -element_rect['x'] + x + width / 2 + x_offset
            relative_element_y = -element_rect['y'] + y + height / 2 + y_offset
        elif cursor_postion == 'TopLeft':
            relative_element_x = -element_rect['x'] + x + x_offset
            relative_element_y = -element_rect['y'] + y + y_offset
        elif cursor_postion == 'TopRight':
            relative_element_x = -element_rect['x'] + x + width + x_offset
            relative_element_y = -element_rect['y'] + y + y_offset
        elif cursor_postion == 'BottomRight':
            relative_element_x = -element_rect['x'] + x + width + x_offset
            relative_element_y = -element_rect['y'] + y + height + y_offset
        elif cursor_postion == 'BottomLeft':
            relative_element_x = -element_rect['x'] + x + x_offset
            relative_element_y = -element_rect['y'] + y + height + y_offset
        option = _transform_option(option, relative_element_x, relative_element_y)
        UiBot.PushContext()
        element = _find_element(_element, _timeout)
        
        UiBot.InvokeRobotCore(element, 'MouseAction', [button, click_type, _timeout, json.dumps(option)])
        time_delay(delay_after)
    except Exception as e:
        if not continue_on_err:
            UiBot.PopContext()
            raise e
    UiBot.PopContext()


def Hover(_element, _rect, _mage_cfg, _text, _rule, _occurrence, _timeout, _option = _default_ocr_text_option):
    param_util = ParamUtil()
    option = param_util.get_option_param(_option)
    continue_on_err = param_util.get_continue_on_err_param(option)
    try:
        delay_before, delay_after = param_util.get_delay_param(option)
        cursor_postion = param_util.get_cursor_postion_param(option)
        x_offset = param_util.get_x_offset_param(option)
        y_offset = param_util.get_y_offset_param(option)

        time_delay(delay_before)
        element_rect, text_rect = _Find(_element, _rect, _mage_cfg, _text, _rule, _occurrence, _timeout, option)
        x = text_rect['x']
        y = text_rect['y']
        width = text_rect['width']
        height = text_rect['height']

        # calculate relative x,y for MouseAction
        relative_element_x, relative_element_y = 0, 0
        if cursor_postion == 'Center':
            relative_element_x = -element_rect['x'] + x + width / 2 + x_offset
            relative_element_y = -element_rect['y'] + y + height / 2 + y_offset
        elif cursor_postion == 'TopLeft':
            relative_element_x = -element_rect['x'] + x + x_offset
            relative_element_y = -element_rect['y'] + y + y_offset
        elif cursor_postion == 'TopRight':
            relative_element_x = -element_rect['x'] + x + width + x_offset
            relative_element_y = -element_rect['y'] + y + y_offset
        elif cursor_postion == 'BottomRight':
            relative_element_x = -element_rect['x'] + x + width + x_offset
            relative_element_y = -element_rect['y'] + y + height + y_offset
        elif cursor_postion == 'BottomLeft':
            relative_element_x = -element_rect['x'] + x + x_offset
            relative_element_y = -element_rect['y'] + y + height + y_offset
        option = _transform_option(option, relative_element_x, relative_element_y)
        UiBot.PushContext()
        element = _find_element(_element, _timeout)
        
        UiBot.InvokeRobotCore(element, 'MouseHover', [_timeout, json.dumps(option)])
        time_delay(delay_after)
    except Exception as e:
        if not continue_on_err:
            UiBot.PopContext()
            raise e
    UiBot.PopContext()

class BackendTaskError(Exception):
    pass

#文档抽取类型
# 文档抽取验证并获取结果
def NLPDocumentExtract(_file, _mage_cfg):
    pubkey, secret, base_url = r'', r'', r''
    _time_out = 30000
    log_record = LogRecord()
    try:
        #解析并校验输入参数的合法性        
        param_util = ParamUtil()
        doc_file = param_util.get_valid_file_param(_file)            
        pubkey, secret, base_url,ai_name = param_util.get_mage_access_param_ex(_mage_cfg)
        #构造并发送网络请求                
        mage_client = MageClient(base_url)        
        msg_header = mage_client.generate_header(pubkey, secret)        
        msg_body = mage_client.generate_file_body(doc_file, False)        
        time_out = param_util.get_time_out_param(_time_out)
        
        start_time = datetime.datetime.now()
        retry_num = 1
        res_data = None
        
        for i in range(retry_num):#重试3次
            try:
                left_time_out = time_out - (datetime.datetime.now() - start_time).seconds * 1000
                if left_time_out <= 0:
                    i = retry_num - 1
                    raise Exception(UiBot.GetString("Mage/TimeOut"))
                res_data = mage_client.do_request(url_route_dict['docextract_create'], msg_header, msg_body, left_time_out)
                break
            except Exception as e:
                if i == retry_num - 1:#重试结束，若仍报错，则把异常抛出，让外面捕获处理
                    raise Exception('{0}'.format(e))
                pass

        #简单地后处理网络返回的响应消息
        task_id_result = process_task_result(res_data)

        #根据task_id每隔5秒去取结果
        wait_start = datetime.datetime.now()
        body_dict = dict()
        body_dict['task_id'] = task_id_result
        error_times = 0        
        while True:
            if UiBot.IsStop():
                break

            mage_client.show_tip(wait_start)
            try:
                ret = mage_client.do_request(url_route_dict['docextract_query'], msg_header, body_dict, left_time_out)
                try:
                    check_correct_state(ret)
                    if "data" not in ret:
                        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
                except Exception as e:
                    raise BackendTaskError(e)
                data = ret["data"]
                error_times = 0
                if data.get("status") == 3:
                    log_record.upload_log(pubkey, secret, 1, 'NLPDocumentExtract', base_url)
                    data["ai_function"] = "nlp_doc"
                    data["ai_name"] = ai_name
                    return data
                elif data.get("status") == 4:
                    raise BackendTaskError(UiBot.GetString("Mage/HTTP_RECG_FAILED") + '{0}'.format("status=4"))
                else:
                    print("查询任务结果成功，但任务未完成，5s 后重试。 status = ", ret.get("status"))
            except BackendTaskError as be:
                raise be
            except Exception as e:
                print("查询任务结果，失败，5s 后重试:", e)
                error_times += 1

            if not UiBot.IsStop():
                time.sleep(5)

    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'NLPDocumentExtract', base_url)
        msg = '{0}'.format(e)
        raise Exception(msg)

# 获取文档抽取验证协同结果中的字段内容
def ExtractDocumentInfo(nlpResult, keyList):
    if type(nlpResult) is list:
        raise Exception(UiBot.GetString("Mage/OcrResultIsAnArray"))
    if 'ai_function' not in nlpResult or nlpResult['ai_function'] != 'nlp_doc':
        raise Exception(UiBot.GetString("Mage/NotANLPDocResult"))

    if type(keyList) != list:
        raise Exception(UiBot.GetString("RpaCollaboration/KeyListTypeError"))
    if len(keyList) == 0:
        raise Exception(UiBot.GetString('RpaCollaboration/KeyListIsEmpty'))
    if 'ai_name' not in nlpResult or nlpResult['ai_name'] != keyList[0]:
        raise Exception(UiBot.GetString("Mage/AiNameNotMatch"))

    typeKey = _SafeGetValue(nlpResult, 'type_key')
    # if 'resume' != typeKey:
    #     raise Exception(UiBot.GetString("Mage/CardInvoiceTypeNotMatch") % (typeKey,))

    fieldsList = _SafeGetValue(nlpResult, 'fields')
    bGetValue = False
    retData = []
    field_key = "description"
    fieldvalue = "values"
    fieldkey_value = keyList[-1]#取最后一个数据
    for field in fieldsList:
        if (field_key in field) and (fieldvalue in field):
            if fieldkey_value == field[field_key]:
                for value in field[fieldvalue]:
                    content = _SafeGetValue(value, 'content')
                    retData.append(content)
                bGetValue = True
                break
    
    if not bGetValue:
        raise Exception(UiBot.GetString("RpaCollaboration/OcrResultNoKeyValueFound") % fieldkey_value)
    return retData

# 提取自定义模板识别命令表格内容
def ExtractOCRTemplateTableInfo(ocrTemplateResult, keyList):
    if type(ocrTemplateResult) is list:
        raise Exception(UiBot.GetString("Mage/OcrResultIsAnArray"))
    if 'ai_function' not in ocrTemplateResult or ocrTemplateResult['ai_function'] != 'ocr_template':
        raise Exception(UiBot.GetString("Mage/NotAnTemplateResult"))
    
    if type(keyList) != list:
        raise Exception(UiBot.GetString("Mage/TemplateListTypeError"))
    if len(keyList) == 0:
        raise Exception(UiBot.GetString('Mage/TemplateListIsEmpty'))

    paramUtil = ParamUtil()
    templateName = keyList[-1]
    _templateName = _SafeGetValue(ocrTemplateResult, 'template_name')
    if _templateName != templateName:
        raise Exception(UiBot.GetString("Mage/TemplateNameNotMatch") % (_templateName, templateName))
    itemRaw = _SafeGetValue(ocrTemplateResult, 'raw')
    tables_result = copy.deepcopy(itemRaw)
    _SafeGetValue(tables_result, 'tables')
    _SafeGetValue(tables_result, 'items')
    page_number = 1#直接标识1即可，因为入参结果就是单个数据了

    for item in tables_result["tables"]:
        item["page_number"] = page_number
    for item in tables_result["items"]:
        item["page_number"] = page_number

    table_extract_util = TableExtractUtil()
    table_extract_util.parse_table_result(tables_result)
    table_list = list()
    for table_item in table_extract_util.tables:
        table_list.append(table_item.row_info)
    return table_list

#------------------------------------------------------
#文档自训练抽取
# 发起文档自训练抽取并获取结果
def NLPDocumentMultiplePageExtract(_file, _mage_cfg):
    pubkey, secret, base_url = r'', r'', r''
    _time_out = 30000
    log_record = LogRecord()
    try:
        #解析并校验输入参数的合法性        
        param_util = ParamUtil()
        doc_file = param_util.get_valid_file_param(_file)            
        pubkey, secret, base_url,ai_name = param_util.get_mage_access_param_ex(_mage_cfg)
        #构造并发送网络请求                
        mage_client = MageClient(base_url)        
        msg_header = mage_client.generate_header(pubkey, secret)        
        msg_body = mage_client.generate_file_body(doc_file, False)        
        time_out = param_util.get_time_out_param(_time_out)
        
        res_data = None        
        try:
            res_data = mage_client.do_request(url_route_dict['idp_extractor_create'], msg_header, msg_body, time_out)
        except Exception as e:
            raise Exception('{0}'.format(e))

        #简单地后处理网络返回的响应消息
        task_id_result = process_task_result(res_data)

        #根据task_id每隔5秒去取结果
        wait_start = datetime.datetime.now()
        body_dict = dict()
        body_dict['task_id'] = task_id_result
        error_times = 0        
        while True:
            if UiBot.IsStop():
                break

            mage_client.show_tip(wait_start)
            try:
                ret = mage_client.do_request(url_route_dict['idp_extractor_query'], msg_header, body_dict, time_out)
                try:
                    check_correct_state(ret)
                    if "data" not in ret:
                        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
                except Exception as e:
                    raise BackendTaskError(e)
                data = ret["data"]
                error_times = 0
                if data.get("status") == 4:
                    log_record.upload_log(pubkey, secret, 1, 'NLPDocumentMultiplePageExtract', base_url)
                    data["ai_function"] = "idp_extractor"
                    data["ai_name"] = ai_name
                    return data
                elif data.get("status") == 5:
                    raise BackendTaskError(UiBot.GetString("Mage/HTTP_RECG_FAILED") + '{0}'.format("status=5"))
                else:
                    print("查询任务结果成功，但任务未完成，5s 后重试。 status = ", ret.get("status"))
            except BackendTaskError as be:
                raise be
            except Exception as e:
                print("查询任务结果，失败，5s 后重试:", e)
                error_times += 1

            if not UiBot.IsStop():
                time.sleep(5)

    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'NLPDocumentMultiplePageExtract', base_url)
        msg = '{0}'.format(e)
        raise Exception(msg)

# 获取文档自训练抽取的字段列表
def ExtractMultiplePageList(_mage_cfg):
    pubkey, secret, base_url = r'', r'', r''
    _time_out = 30000
    log_record = LogRecord()
    try:
        #解析并校验输入参数的合法性        
        param_util = ParamUtil()
        pubkey, secret, base_url,ai_name = param_util.get_mage_access_param_ex(_mage_cfg)
        #构造并发送网络请求                
        mage_client = MageClient(base_url)        
        msg_header = mage_client.generate_header(pubkey, secret)        
        msg_body = mage_client.generate_body_for_field_list()
        time_out = param_util.get_time_out_param(_time_out)
        
        res_data = None        
        try:
            res_data = mage_client.do_request(url_route_dict['field_list'], msg_header, msg_body, time_out)
        except Exception as e:
            raise Exception('{0}'.format(e))

        #简单地后处理网络返回的响应消息
        retData = process_idp_page_result(res_data)
        log_record.upload_log(pubkey, secret, 1, 'ExtractMultiplePageList', base_url)
        return retData
    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'ExtractMultiplePageList', base_url)
        msg = '{0}'.format(e)
        raise Exception(msg)

# 获取文档自训练抽取的字段内容
def ExtractMultiplePageInfo(idpResult, keyList):
    if type(idpResult) is list:
        raise Exception(UiBot.GetString("Mage/OcrResultIsAnArray"))
    if 'ai_function' not in idpResult or idpResult['ai_function'] != 'idp_extractor':
        raise Exception(UiBot.GetString("Mage/NotAnTemplateResult"))
    
    if type(keyList) != list:
        raise Exception(UiBot.GetString("RpaCollaboration/KeyListTypeError"))
    if len(keyList) == 0:
        raise Exception(UiBot.GetString('RpaCollaboration/KeyListIsEmpty'))
    if 'ai_name' not in idpResult or idpResult['ai_name'] != keyList[0]:
        raise Exception(UiBot.GetString("Mage/AiNameNotMatch"))

    fieldsList = _SafeGetValue(idpResult, 'fields')
    bGetValue = False
    retData = []
    fieldkey_value = keyList[-1]#取最后一个数据
    for field in fieldsList:
        field_type = _SafeGetValue(field, 'field_type')
        field_name = _SafeGetValue(field, 'field_name')                   
        if fieldkey_value == field_name:
            if field_type == 1:#字符串
                text = _SafeGetValue(field, 'text')
                retData = _SafeGetValue(text, 'value')
                bGetValue = True
            else:#数组
                text_list = _SafeGetValue(field, 'text_list')
                values = _SafeGetValue(text_list, 'values')
                for val in values:
                    value = _SafeGetValue(val, 'value')
                    retData.append(value)
                bGetValue = True
            break
    
    if not bGetValue:
        raise Exception(UiBot.GetString("RpaCollaboration/OcrResultNoKeyValueFound") % fieldkey_value)
    return retData


#------------------------------------------------------
#单据自训练抽取
# 发起单据自训练抽取并获取结果
def NLPDocumentSinglePageExtract(_file, _mage_cfg):
    pubkey, secret, base_url = r'', r'', r''
    _time_out = 30000
    log_record = LogRecord()
    try:
        #解析并校验输入参数的合法性        
        param_util = ParamUtil()
        doc_file = param_util.get_valid_file_param(_file)            
        pubkey, secret, base_url,ai_name = param_util.get_mage_access_param_ex(_mage_cfg)
        #构造并发送网络请求                
        mage_client = MageClient(base_url)        
        msg_header = mage_client.generate_header(pubkey, secret)        
        msg_body = mage_client.generate_file_body(doc_file, False)
        time_out = param_util.get_time_out_param(_time_out)
        
        res_data = None        
        try:
            res_data = mage_client.do_request(url_route_dict['idp_extractor_single_create'], msg_header, msg_body, time_out)
        except Exception as e:
            raise Exception('{0}'.format(e))

        #简单地后处理网络返回的响应消息
        task_id_result = process_task_result(res_data)

        #根据task_id每隔5秒去取结果
        wait_start = datetime.datetime.now()
        body_dict = dict()
        body_dict['task_id'] = task_id_result
        error_times = 0        
        while True:
            if UiBot.IsStop():
                break

            mage_client.show_tip(wait_start)
            try:
                ret = mage_client.do_request(url_route_dict['idp_extractor_single_query'], msg_header, body_dict, time_out)
                try:
                    check_correct_state(ret)
                    if "data" not in ret:
                        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
                except Exception as e:
                    raise BackendTaskError(e)
                data = ret["data"]
                error_times = 0
                if data.get("status") == 4:
                    log_record.upload_log(pubkey, secret, 1, 'NLPDocumentSinglePageExtract', base_url)
                    data["ai_function"] = "idp_extractor_single"
                    data["ai_name"] = ai_name
                    return data
                elif data.get("status") == 5:
                    raise BackendTaskError(UiBot.GetString("Mage/HTTP_RECG_FAILED") + '{0}'.format("status=5"))
                else:
                    print("查询任务结果成功，但任务未完成，5s 后重试。 status = ", ret.get("status"))
            except BackendTaskError as be:
                raise be
            except Exception as e:
                print("查询任务结果，失败，5s 后重试:", e)
                error_times += 1

            if not UiBot.IsStop():
                time.sleep(5)

    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'NLPDocumentSinglePageExtract', base_url)
        msg = '{0}'.format(e)
        raise Exception(msg)

# 获取单据自训练抽取字段列表
def ExtractSinglePageList(_mage_cfg):
    pubkey, secret, base_url = r'', r'', r''
    _time_out = 30000
    log_record = LogRecord()
    try:
        #解析并校验输入参数的合法性        
        param_util = ParamUtil()
        pubkey, secret, base_url,ai_name = param_util.get_mage_access_param_ex(_mage_cfg)
        #构造并发送网络请求                
        mage_client = MageClient(base_url)        
        msg_header = mage_client.generate_header(pubkey, secret)        
        msg_body = mage_client.generate_body_for_field_list()
        time_out = param_util.get_time_out_param(_time_out)
        
        res_data = None        
        try:
            res_data = mage_client.do_request(url_route_dict['field_list'], msg_header, msg_body, time_out)
        except Exception as e:
            raise Exception('{0}'.format(e))

        #简单地后处理网络返回的响应消息
        retData = process_idp_page_result(res_data)
        log_record.upload_log(pubkey, secret, 1, 'ExtractSinglePageList', base_url)
        return retData
    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'ExtractSinglePageList', base_url)
        msg = '{0}'.format(e)
        raise Exception(msg)

# 获取单据自训练抽取的字段内容
def ExtractSinglePageInfo(idpResult, keyList):
    if type(idpResult) is list:
        raise Exception(UiBot.GetString("Mage/OcrResultIsAnArray"))
    if 'ai_function' not in idpResult or idpResult['ai_function'] != 'idp_extractor_single':
        raise Exception(UiBot.GetString("Mage/NotAnTemplateResult"))
    
    if type(keyList) != list:
        raise Exception(UiBot.GetString("RpaCollaboration/KeyListTypeError"))
    if len(keyList) == 0:
        raise Exception(UiBot.GetString('RpaCollaboration/KeyListIsEmpty'))
    if 'ai_name' not in idpResult or idpResult['ai_name'] != keyList[0]:
        raise Exception(UiBot.GetString("Mage/AiNameNotMatch"))

    fieldsList = _SafeGetValue(idpResult, 'fields')
    bGetValue = False
    retData = []
    fieldkey_value = keyList[-1]#取最后一个数据
    for field in fieldsList:
        field_type = _SafeGetValue(field, 'field_type')
        field_name = _SafeGetValue(field, 'field_name')                   
        if fieldkey_value == field_name:
            if field_type == 1:#字符串
                text = _SafeGetValue(field, 'text')
                retData = _SafeGetValue(text, 'value')
                bGetValue = True
            else:#数组
                text_list = _SafeGetValue(field, 'text_list')
                values = _SafeGetValue(text_list, 'values')
                for val in values:
                    value = _SafeGetValue(val, 'value')
                    retData.append(value)
                bGetValue = True
            break
    
    if not bGetValue:
        raise Exception(UiBot.GetString("RpaCollaboration/OcrResultNoKeyValueFound") % fieldkey_value)
    return retData

#------------------------------------------------------
#文档分类
# 分类文档
def NLPDocumentClassificationExtract(_file, _mage_cfg):
    pubkey, secret, base_url = r'', r'', r''
    _time_out = 30000
    log_record = LogRecord()
    try:
        #解析并校验输入参数的合法性        
        param_util = ParamUtil()
        doc_file = param_util.get_valid_file_param(_file)            
        pubkey, secret, base_url,ai_name = param_util.get_mage_access_param_ex(_mage_cfg)
        #构造并发送网络请求                
        mage_client = MageClient(base_url)        
        msg_header = mage_client.generate_header(pubkey, secret)        
        msg_body = mage_client.generate_file_body(doc_file, False)
        time_out = param_util.get_time_out_param(_time_out)
        
        res_data = None        
        try:
            res_data = mage_client.do_request(url_route_dict['idp_doc_classification_create'], msg_header, msg_body, time_out)
        except Exception as e:
            raise Exception('{0}'.format(e))

        #简单地后处理网络返回的响应消息
        task_id_result = process_task_result(res_data)

        #根据task_id每隔5秒去取结果
        wait_start = datetime.datetime.now()
        body_dict = dict()
        body_dict['task_id'] = task_id_result
        error_times = 0        
        while True:
            if UiBot.IsStop():
                break

            mage_client.show_tip(wait_start)
            try:
                ret = mage_client.do_request(url_route_dict['idp_doc_classification_query'], msg_header, body_dict, time_out)
                try:
                    check_correct_state(ret)
                    if "data" not in ret:
                        raise Exception(UiBot.GetString("Mage/HTTP_RES_FORMAT_ERR"))
                except Exception as e:
                    raise BackendTaskError(e)
                data = ret["data"]
                error_times = 0
                if data.get("status") == 1:
                    log_record.upload_log(pubkey, secret, 1, 'NLPDocumentClassificationExtract', base_url)
                    data["ai_function"] = "idp_doc_classification"
                    data["ai_name"] = ai_name
                    return data
                elif data.get("status") == 2 or data.get("status") == 3:
                    raise BackendTaskError(UiBot.GetString("Mage/HTTP_RECG_FAILED") + '{0}'.format("status=2 or 3"))
                else:
                    print("查询任务结果成功，但任务未完成，5s 后重试。 status = ", ret.get("status"))
            except BackendTaskError as be:
                raise be
            except Exception as e:
                print("查询任务结果，失败，5s 后重试:", e)
                error_times += 1

            if not UiBot.IsStop():
                time.sleep(5)

    except Exception as e:
        log_record.upload_log(pubkey, secret, 0, 'NLPDocumentClassificationExtract', base_url)
        msg = '{0}'.format(e)
        raise Exception(msg)

# 获取文档分类结果
def ExtractClassificationInfo(idpResult):
    if type(idpResult) is list:
        raise Exception(UiBot.GetString("Mage/OcrResultIsAnArray"))
    if 'ai_function' not in idpResult or idpResult['ai_function'] != 'idp_doc_classification':
        raise Exception(UiBot.GetString("Mage/NotAnDocClassifyResult"))
    
    result = _SafeGetValue(idpResult, 'result')
    page_results = _SafeGetValue(result, 'page_results')
    page_results_tmp = copy.deepcopy(page_results)
    for page in page_results_tmp:
        type_results = _SafeGetValue(page, 'type_results')
        if type(type_results) == list and len(type_results) != 0:
            value = type_results[0]
            page["type_results"] = value#取第一个最高值
    return page_results_tmp


# -------------<------------------------

if __name__ == '__main__':
    print('UiBot Mage')


#chatgpt与各种库的引入
import os
import time
import openai
os.environ["OPENAI_API_TYPE"] = "azure"
os.environ["OPENAI_API_BASE"] = "https://laiye-openai.openai.azure.com/"
os.environ["OPENAI_API_VERSION"] = "2023-03-15-preview"
os.environ["OPENAI_API_KEY"] = '29fea35d1b3c42ce8ac2c9e83dd66d5d'

from langchain.chat_models import AzureChatOpenAI
chat = AzureChatOpenAI(
    deployment_name="gpt4-test",
  model_name="gpt-4-32k"
)

from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage
)
from langchain.prompts import (
    ChatPromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain import PromptTemplate
from langchain.chains import ConversationChain
from langchain.memory import ConversationSummaryBufferMemory
from langchain.memory import ConversationBufferMemory

response_list = []

#将代码分块后进行code review的函数
def code_divided():
    human_template_1="""
你是一个擅长做code review的人工智能助手

一段完整的代码被分成了{sum}块依次上传，你将依次对这{sum}块代码进行code review，从而得到对该段完整代码的code review结果

在对当前代码块进行code review时，你要结合此前的代码块实现的功能，来分析当前代码块

一定要注意当前代码块与此前代码块的上下文关联！

请始终记住一共需要对{sum}块代码进行code review
"""
    human_template_2="""
一共有{sum}块代码需要code review，当前进行到第{num}块代码。
这是第{num}块代码:

{code_for_review}
"""
    human_message_prompt =  PromptTemplate.from_template(human_template_1)
    messages = human_message_prompt.format(sum=len(texts))
    
    conversation = ConversationChain(
        llm=chat,
        memory=ConversationSummaryBufferMemory(llm=chat, max_token_limit=22000),
        verbose=True,
    )
    conversation(messages)
    
    f = open('review结果/response','a')
    for i in range(len(texts)):
        human_message_prompt =  PromptTemplate.from_template(human_template_2)
        messages = human_message_prompt.format(sum=len(texts),num=str(i+1),code_for_review=texts[i])
        response_list.append(conversation(messages))
        
        f.write('####################################\n')
        f.write('##第'+str(i+1)+'块代码：\n')
        f.write('####################################\n')
        f.write(texts[i].page_content+'\n')
        f.write('####################################\n')
        f.write('##第'+str(i+1)+'块代码的code review结果\n')
        f.write('####################################\n')
        f.write(response_list[i]['response']+'\n\n')
    f.close()

#将代码看作一个整体进行code review的函数
def code_in_one_piece():
    human_template_1="""
你是一个擅长做code review的人工智能助手

一段完整的代码被分成了{sum}块依次上传，你将等待这{sum}块代码全部上传后，才对整段代码进行code review，在{sum}块代码全部上传前，你不能进行code review

在进行code review时，注意考虑各个代码块之间的上下文关联
"""
    human_template_2="""
一共{sum}块代码，请等待{sum}块代码全部上传以后再进行code review
这是第{num}块代码:

{code_for_review}
"""
    human_message_prompt =  PromptTemplate.from_template(human_template_1)
    messages = human_message_prompt.format(sum=len(texts))
    
    conversation = ConversationChain(
        llm=chat,
        memory=ConversationBufferMemory(),
        verbose=True,
    )
    conversation(messages)
    
    for i in range(len(texts)):
        human_message_prompt =  PromptTemplate.from_template(human_template_2)
        messages = human_message_prompt.format(sum=len(texts),num=str(i+1),code_for_review=texts[i])
        out=conversation(messages)
    
    f = open('review结果/response','w')
    f.write(out['response'])
    f.close()

#读取代码并将代码分块
from langchain.document_loaders import TextLoader

root_dir = "code_for_review"
print("即将对如下程序进行code review:\n\n")
docs = []
for dirpath, dirnames, filenames in os.walk(root_dir):
    for file in filenames:
        
        if file.endswith(".py") and "/.venv/" not in dirpath:
            try:
                loader = TextLoader(os.path.join(dirpath, file), encoding="utf-8")
                docs.extend(loader.load_and_split())
            except Exception as e:
                pass
        print(str(file)+"     当前被划分为"+f"{len(docs)}"+"块")

time.sleep(15)

from langchain.text_splitter import CharacterTextSplitter

text_splitter = CharacterTextSplitter(chunk_size=2000, chunk_overlap=0)
texts = text_splitter.split_documents(docs)
print(str(file)+"     当前被重新划分为"+f"{len(texts)}"+"块")

#根据代码的长度选择：
# 1、将代码进行分块code review
# 2、将代码看作一个整体进行code review
sum=0
for i in range(len(texts)):
    sum += len(texts[i].page_content)
if (sum<70000):
    code_divided()
    print("代码将被分块以后进行code review\n")
else:
    code_in_one_piece()
    print("代码将以一个整体进行code review\n")

print("code review结果将被保存在 review结果 文件夹中\n")
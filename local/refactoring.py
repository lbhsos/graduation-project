# -*- coding: utf-8 -*-
"""
Created on Wed Feb 20 19:59:07 2019

@author: YuJeong
"""

#========================Word2Vec===================================
from gensim.models import Word2Vec 
#========================가중치 배열 계산============================
import gensim.models as g
import pandas as pd
from scipy.spatial.distance import squareform, pdist
#=============================표준화=================================
from konlpy.tag import Twitter
import re
import numpy as np
import copy 

category = ['결제', '계정', '서버','구성','연출','캐릭터','시스템','기타']
pay_words = ["결제/Noun","구입/Noun","구매/Noun","현질/Noun","환불/Noun"] #결제
id_words = ['계정/Noun','아이디/Noun','연동/Noun','구글/Noun','로그인/Noun'] #계정
config_words = ["버그/Noun","서버/Noun","접속/Noun","로딩/Noun","렉/Noun"] #구성, 기획
production_words = ["배경/Noun","그래픽/Noun","퀄리티/Noun","사운드/Noun","디자인/Noun"] #연출, 액션
character_words = ["스킬/Noun","너프/Noun","영웅/Noun","캐릭터/Noun","캐릭/Noun"] #캐릭터, 체력
sys_words = ["용량/Noun","다운/Noun","앱/Noun","실행/Noun","설치/Noun"] #시스템
dissatis_words = ["광고/Noun","신고/Noun","채팅/Noun","욕/Noun","처벌/Noun"] #불만
category_in= pay_words + id_words + config_words + production_words + character_words + sys_words + dissatis_words
cate_length=len(category_in) 
d_length=300 #카테고리 분류 할 리뷰 개수


def tokenize(doc):
    pos_tagger = Twitter()
    return ['/'.join(t) for t in pos_tagger.pos(doc, norm=True, stem=True)]

def remove_emoji():
    emoji_pattern = re.compile("["
    u"\U0001F600-\U0001F64F"  # emoticons
    u"\U0001F300-\U0001F5FF"  # symbols & pictographs
    u"\U0001F680-\U0001F6FF"  # transport & map symbols
    u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                   "]+", flags=re.UNICODE)
    return emoji_pattern

def read_raw_data(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        print('loading data')
        data = []
        tokenized_data = []
        categ_data = []
        for line in f.read().splitlines():
            data_temp = remove_emoji().sub(r'', line)
            data.append(data_temp.split('\t'))   
        print('pos tagging to token')
        tokenized_data = [(tokenize(row[1])) for row in data[0:]]
        categ_data =[(row[1]) for row in data[0:]]
    return (tokenized_data, categ_data)

def preprocess_token(data):
#    tokens = [t for d in data for t in d]
    print("토큰 전처리")
   # data_length=len(data)
    tokenized=[]
    d_l=-1
    for sentence in data:
        d_l+=1
        line=[]
        tempS=str(sentence)
        toke3=tempS.strip().split(', ')
        toke_len=len(toke3)
        for t in range(toke_len):
            toke=toke3[t].replace("'","").replace("[","").replace("]","")
            if "Noun" in toke:
                line.append(toke)
            elif "Verb" in toke:
                line.append(toke)
            elif "Adjective" in toke:
                line.append(toke)                      
        tokenized.append(list(line))
    return tokenized

def word2vec(tokenized): #word2vec 모델 생성 및 vocab 생성
    model=Word2Vec(tokenized, size=100, window = 2, min_count=20, workers=4, iter=100, sg=1)
    model_name = 'word2vec_model'
    print("modeling word2vec")
    model.save(model_name)
    return model_name

def wordvector_matrix(model_name): #word2vec의 결과 단어벡터 행렬
    print("build vocab")
    model = g.Doc2Vec.load(model_name) 
    vocab = list(model.wv.vocab)
    df = pd.DataFrame(model[vocab], index = vocab)
    return df

def euclidian_distance_matrix(df) :
    eucli_dm = pd.DataFrame(squareform(pdist(df.iloc[:, 1:])),columns=df.index.unique(), index=df.index.unique())
    return eucli_dm

def weighted_matrix(eucli_dm): #정규 분포 사용하여 가중치 행렬로 변환
    df_theme=eucli_dm[category_in]
        # 새로 카테고리 배열들 합 구하기스
    print("가중치 행렬 계산")
    #df_pow=pd.DataFrame.pow(df_theme,fill_value=None)
    df_pow=np.power(df_theme, 2)
    df_pow.loc['temp'] = [0 for n in range(cate_length)]#temp 행 추가
    df_exp=np.exp(-df_pow/100)
    df_exp1 =  df_exp.drop("temp")
    df_pow =  df_pow.drop("temp", axis = 0)
    df_length=len(df_exp1.index)
    sum=0
    for j in range(cate_length):         
        for i in range(df_length):
            sum+=df_exp1.iloc[i,j]
        df_mean=sum/df_length
        tuneweight=0.5-df_mean
        for k in range(df_length):
            df_exp1.iloc[i,j]-=tuneweight
        sum=0
  #  df_exp1 이 가중치행렬
    return df_exp1

def term_document_matrix(content):
    print("TDM 배열")
    content = pd.DataFrame(content) 
    content.columns=["content"] 
    categ_data = pd.DataFrame(content)
    return categ_data

def compute_inner_product(data, df_exp1):
    TDM=[[0 for col in range(60)] for row in range(d_length)] 
    w=[0]*60
    #f1-f6 col, 각 리뷰 row
    tdm_sum=[[0 for col in range(cate_length+1)] for row in range(d_length)]
    for i in range(d_length):
        df_string=str(data[i])
        w=df_string.split(', ')
        ##df마지막에 length추가하기 TODO      
        token_length=len(w)
        if(token_length>=60):
            token_length=60
        df_flag=[0]*(cate_length)
        if(token_length>5):
            for j in range(token_length):
                tempWord=w[j].replace("'","").replace("[","").replace("]","")
                ##단어 존재하는지 확인
                for k in range(cate_length): # 이 for문 설명좀 해쥬세유,,
                    try:
                        df_value=df_exp1.loc[tempWord,category_in[k]]
                        #1로배정
                    except KeyError as e:
                        TDM[i][j]=0
                    else:
                        if(df_flag[k]==1): # 
                            df_value=0
                            continue
                        else:
                            df_flag[k]=1
                            TDM[i][j]=1 ##몇번 나왔는지까지 
                            tdm_sum[i][k]+=(df_value) 
                            df_value=0
                df_flag=[0 for m in range(cate_length)]
        else:##TOO SHORT
            tdm_sum[i][cate_length]=1000
    return tdm_sum
    
def compute_TDM_sum(tdm_sum):
    TDM_SUM=[[0 for col in range(9)] for row in range(d_length)]
    temp_sum=[0]*9
    for line in range(d_length):
        for col in range(cate_length):
            if ((col>=0 and col<=4)): #결제
                temp_sum[0]+=tdm_sum[line][col]
            elif ((col>=5 and col<=9)): #계정
                temp_sum[1]+=tdm_sum[line][col]
            elif ((col>=10 and col<=14)): #서버
                temp_sum[2]+=tdm_sum[line][col]
            elif ((col>=15 and col<=19)): #구성
                temp_sum[3]+=tdm_sum[line][col]
            elif ((col>=20 and col<=24)): #연
                temp_sum[4]+=tdm_sum[line][col]
            elif ((col>=25 and col<=29)): #캐릭터
                temp_sum[5]+=tdm_sum[line][col]
            elif ((col>=30 and col<=34)): #시스템
                temp_sum[6]+=tdm_sum[line][col]
            elif ((col>=35 and col<=39)): #기타
                temp_sum[7]+=tdm_sum[line][col]
            elif ((col==40)): #TOO_SHorT
                temp_sum[8]+=tdm_sum[line][col]          
        for i in range(0, 9):
            TDM_SUM[line][i]=temp_sum[i]
        temp_sum=[0]*9  
    return TDM_SUM

def classification(TDM_SUM): 
    print("카테고리 max으로 분류하기")
    categ_arr=[]
    categ_arr = categ_data.as_matrix()
    f=[k for k in range(9)]
    for col in range(9):
        f[col]=[]
    cate_result=[]
    for i in range(d_length):
        if (max(TDM_SUM[i]) != 0): #짧지않다
            desc = copy.deepcopy(TDM_SUM)
            desc[i].sort(reverse=True)#내림차순
            #임계값
            threshold=0.35
            max_score=desc[i][0]
            cate_result=[]
            max_index=TDM_SUM[i].index(desc[i][0])
            if max_index==0 :
                categ_result = "결제"
                f[max_index].append([categ_arr[i]])
            elif max_index == 1:
        
                categ_result = "계정"
                f[max_index].append([categ_arr[i]])
            elif max_index == 2:
          
                categ_result = "서버"
                f[max_index].append([categ_arr[i]])
            elif max_index == 3:
        
                categ_result = "구성"
                f[max_index].append([categ_arr[i]])
            elif max_index == 4:
   
                categ_result = "연출"
                f[max_index].append([categ_arr[i]])
            elif max_index == 5:
       
                categ_result = "캐릭터"
                f[max_index].append([categ_arr[i]])
            elif max_index == 6:
          
                categ_result = "시스템"
                f[max_index].append([categ_arr[i]])
            elif max_index== 7:
          
                categ_result = "기타"
                f[max_index].append([categ_arr[i]])
            elif max_index == 8:

                categ_result = "TOO_SHORT"
                f[max_index].append([categ_arr[i]])
            cate_result.append(categ_result)
            
            for col in range(1,2):   
                ##0이 중복
                if((max_score-desc[i][col]) <= threshold): 
                    max_index=TDM_SUM[i].index(desc[i][col])
                    if max_index==0 :
                        categ_result = "결제"
                        f[max_index].append([categ_arr[i]])
                    elif max_index == 1:
                        categ_result = "계정"
                        f[max_index].append([categ_arr[i]])
                    elif max_index == 2:
                        categ_result = "서버"
                        f[max_index].append([categ_arr[i]])
                    elif max_index == 3:
                        categ_result = "구성"
                        f[max_index].append([categ_arr[i]])
                    elif max_index == 4:
                        categ_result = "연출"
                        f[max_index].append([categ_arr[i]])
                    elif max_index == 5:
                        categ_result = "캐릭터"
                        f[max_index].append([categ_arr[i]])
                    elif max_index == 6:
                  
                        categ_result = "시스템"
                        f[max_index].append([categ_arr[i]])
                    elif max_index== 7:
                  
                        categ_result = "기타"
                        f[max_index].append([categ_arr[i]])
                    elif max_index == 8:
                    
                        categ_result = "TOO_SHORT"
                        f[max_index].append([categ_arr[i]])
                    cate_result.append(categ_result)
         #   print(i,': ',categ_arr[i],' ',str(cate_result))
    return f
     
def result(f):
    result_review = []
    for i in range(9):
        result_review.append(pd.DataFrame(f[i]))
    return result_review   

def print_result(result_review):
    for i in range(9):
        print("리뷰 출력", result_review[i].head(10))
        print("len", len(result_review[i]))

if __name__ == '__main__':
    data, content= read_raw_data('C://Users//YuJeong//Desktop//mm.txt') #파일 읽어서 데이터 로딩
    tokenized = preprocess_token(data) #토큰 전처리
    model_name = word2vec(tokenized) #워드투벡 모델 생성
    df = wordvector_matrix(model_name) #워드투벡 결과로 나온 단어벡터 행렬                  
    eucli_dm = euclidian_distance_matrix(df) #유클리디안 거리 이용하여 거리행렬로 변환
    df_exp1 = weighted_matrix(eucli_dm) #정규 분포 사용해서 가중치행렬로 변환
    categ_data = term_document_matrix(content) #TDM 구축
    tdm_sum = compute_inner_product(data, df_exp1) #내적
    TDM_SUM = compute_TDM_sum(tdm_sum) #TDM 합 구하기
    f=classification(TDM_SUM) #카테고리 분류
    result_review = result(f)
    print_result(result_review)
    

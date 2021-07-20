#!/bin/env python3

"""  
    Python 3
    Parse ELSA wave2 pdf file directly to ESRC format, no order needed
"""

import pandas as pd
import numpy as np
import pdfplumber
import re
import os


def rreplace(s, old, new, occurrence):
   """
   Reverse replace string
   """
   li = s.rsplit(old, occurrence)
   return new.join(li)
   

def pdf_to_text(pdf_file, txt_file):
    """
    input: pdf file, page number
    output: raw text
            - remove title, page number 
            - strip '|:', spaces at the beginning of each line
            - strip '*' and ':' at the end of each line
    """
    with pdfplumber.open(pdf_file) as pdf, open(txt_file, 'w+') as f_out: 
        for page in pdf.pages: 
            text = page.extract_text() 
            n = page.page_number 
            new_text = rreplace(text, str(n), '', 1)
            # output from 3rd page
            if n > 2:
                for line in new_text.splitlines():
                    line = line.replace('|', '').lstrip().rstrip()             
                    line = line.replace(':', '').lstrip().rstrip()
                    f_out.write(line + '\n')
                         

def get_sequence(txt_file, sequence_file, question_label_file):
    """
    input: text file 
    output: - sequence_file: module and section name
            - question_label_file
    """
    sequences = ['Section']
    exclude = ['IF', 'ELSE', 'ENDIF', 'DATE', 'TIME', 'RESPONSE', 
               'OUT...', 'ONLY', "TESSA's?", 'RF', 'Allowance', 'STRING[40]', 'TESSA’s?', 'RF)' , 'Bonds?', 
               'EMPTY', 'INCAPACITATED', 'HERE', 'INTERVIEW.', 'LABEL?', 'Range:0..999997',
               'CORRECT.', 'DIFFERENT', 'INTERVIEW?',
               '[Loop', 'LOOP', 'GP?', 'K>', 'Ms).']
    with open(txt_file) as in_file, open(sequence_file, 'w+') as out_sequences, open(question_label_file, 'w+') as out_question_label:
        out_sequences.write('Label\n')
        out_question_label.write('Label\n')
        for line in in_file:
            if line.rstrip().startswith(tuple(sequences)):
                out_sequences.write('%s\n' %(line.rstrip()))
            elif line[0] == '?':
                long_text = line.replace('?', '').lstrip()
                question_label = long_text.split(' ')[0].split('[')[0].split('*')[0].replace('\n', '')
                out_question_label.write('%s\n' %( question_label )  )


def get_condition(txt_file, condition_file, loop_file):
    """
    input: text file 
    output: - condition file
            - loop file
    """
    conditions = ['IF', 'ELSEIF', 'ELSE']
    with open(txt_file) as in_file, open(condition_file, 'w+') as out_condition, open(loop_file, 'w+') as out_loop:
        out_condition.write('Label\n')
        out_loop.write('Label\n')
        prevLine = ''
        for line in in_file:
            if line.startswith(tuple(conditions)) and len(line.split(' ')) > 1:
                nextLine = next(in_file)
                while nextLine != "\n" and not nextLine.startswith('('):
                    line = (line + nextLine).replace('\n', ' ')
                    nextLine2 = next(in_file)
                    nextLine = nextLine2
                out_condition.write('%s\n' %(line.rstrip()))
            elif line.startswith('FOR Loop'):
                nextLine = next(in_file)
                while nextLine != "\n" :
                    line = (line + nextLine).replace('\n', ' ')
                    nextLine2 = next(in_file)
                    nextLine = nextLine2
                out_loop.write('%s\n' %(line.rstrip()))
            prevLine = line
    

def get_question_code_from_questionpair(txt_file, question_1, question_2, debug=False):
    """
    find code list between two question lables
    """
    with open(txt_file, 'r') as content_file:
        content = content_file.read()

    result = re.findall('%s\s*(.*?)%s' % (question_1, question_2), content, re.DOTALL)
    # print(result)
    if not result:
        return []
    if not len(result) == 1:
        pass
    result = result[0]

    if debug:
        print("--------------------"*2)
        print(result)
        print("--------------------"*2)
    codes = re.findall('\n\((\d+)\) (.*)', result)
    # print(codes)
    
    response = re.findall('(YES/NO|AGE|TEXT.*|ARRAY.*|TIMETYPE|DATETYPE|\d+\.\.\d+)', result.split('\n')[0] )
    # print(response)
    # question
    matches = ['\nIF', '\nELSEIF', '\nELSE', '\nENDIF', '\nLOOP FOR', '\nEND FILTER']
    # first occurence
    indexes = [result.find(word) for word in matches]
    if any(x in result for x in matches):
        min_i = min([index for index in indexes if index != -1])
        match = result[min_i:].split(' ')[0]
    else:
        match = ''
        
    if match != '':
        result = result.split(match)[0]
               
    if response != []:
        # print("1 replace response")
        question = result.replace(response[0], '').strip()
    elif codes != []:
        # print("2 replace code")
        question = result.split('\n(' + codes[0][0])[0]
    else:
        question = result.replace('\n', ' ')

    # question literal / instruction

    instruction = ''
    if len(re.findall('(\[Loop:.*\n*.*)]', question)) > 0:
        instruction = re.findall('(\[Loop:.*\n*.*)]', question)[0]
        question = instruction.replace(instruction, '')
    elif len(re.findall('(Attributes.*)', question)) > 0:
        instruction = re.findall('(Attributes.*)', question)[0]
        question = instruction.replace(instruction, '')
    else:
        lines = question.split('\n')
    
        allLine = ''
        for index, line in enumerate(lines):
            if line.isupper() and len(line.split(' ')) > 1 and index <= len(lines) - 2:
                nextLine = lines[index+1]            
                allLine = (line + '\n' + nextLine)
                line = nextLine
            
                instruction = allLine.replace('\n', '')
                question = question.replace(allLine, '')
            elif line.isupper() and len(line.split(' ')) > 1 and index == len(lines) - 1:
                instruction = line
                question = ''
            
    question_text = question.replace('\n', ' ').replace('*','').split('?')[0].lstrip()     

    return question_text, instruction, codes, response


def generate_code_list(txt_file, question_label_file, output_question, output_instruction, output_code, output_response):
    df = pd.read_csv(question_label_file, sep='\t')
    L = df['Label']
    g = get_question_code_from_questionpair

    # print("="*80)

    with open(output_question, 'w+') as out_question, open(output_instruction, 'w+') as out_instruction, open(output_code, 'w+') as out_code, open(output_response, 'w+') as out_response:
        out_question.write('questionLabel\tLiteral\n')
        out_instruction.write('questionLabel\tInstruction\n')
        out_code.write('questionLabel\tValue\tCategory\tcodes_order\n')
        out_response.write('questionLabel\tResponse\n')

        for i in range(0, len(L)-1): 
            # print("="*80) 
            # print("{}: {}..{}".format(i, L[i], L[i+1])) 

            # TODO: generalize this
            if L[i] == 'Hospital':
                question_1 = 'Hospital  YES/NO'
            else:
                question_1 = L[i]

            end_with_number = re.search(r'\d+', L[i+1]) 
            second = re.sub('(_\d+)$', '', L[i+1])
            if end_with_number is not None and second in L:
                question, instruction, code_list, response = g(txt_file, question_1, second)
            else:                 
                question, instruction, code_list, response = g(txt_file, question_1, L[i+1])
                    
            out_question.write('%s\t%s\n' %(L[i], question))
            
            if instruction is not None:
                out_instruction.write('%s\t%s\n' %(L[i], instruction))
            
            if len(code_list) == 0:
                pass
            else:
                #name = "cs_{}".format(L[i])
                for j in range(0, len(code_list)):
                    value = code_list[j][0].replace('"', '').replace("'", "").rstrip().lstrip()
                    cat = code_list[j][1].replace('"', '').replace("'", "").rstrip().lstrip()
                    #print("{}\t{}\t{}\t{}".format(name, value, cat, j+1))
                    out_code.write('%s\t%4d\t%s\t%4d\n' %(L[i], int(value), cat, j+1))
            
            if len(response) == 0:
                pass
            else:
                out_response.write('%s\t%s\n' %(L[i], response[0]))

                              
def main():
    base_dir = '../questionnaire/NCDS-Age-42'
    input_pdf = os.path.join(base_dir, 'NCDS-Age-42-Questionnaire.pdf')
    txt_file = os.path.join(base_dir, 'NCDS-Age-42-Questionnaire_all_pages.txt')

    # clean text
    pdf_to_text(input_pdf, txt_file)

    output_dir = '../questionnaire/NCDS-Age-42/NCDS'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    sequence_file = os.path.join(output_dir, 'sequence.csv')
    question_label_file = os.path.join(output_dir, 'question_label.csv')
    question_file = os.path.join(output_dir, 'question.csv')
    instruction_file = os.path.join(output_dir, 'instruction.csv')
    codelist_file = os.path.join(output_dir, 'codelist.csv')
    response_file = os.path.join(output_dir, 'response.csv')
    condition_file = os.path.join(output_dir, 'condition.csv')
    loop_file = os.path.join(output_dir, 'loop.csv')
    esrc_file = os.path.join(output_dir, 'NCDS_Age_42_ESRC.csv')

    # produce sequence and question label 
    get_sequence(txt_file, sequence_file, question_label_file)
    
    generate_code_list(txt_file, question_label_file, question_file, instruction_file, codelist_file, response_file)

    # produce condition file
    get_condition(txt_file, condition_file, loop_file)

    # combine to get ESRC format
    df_sequence = pd.read_csv(sequence_file, sep='\t')
    df_sequence['item_type'] = 'sequence'
    df_sequence['content'] = df_sequence['Label']
  
    df_question = pd.read_csv(question_file, sep='\t')
    df_instruction = pd.read_csv(instruction_file, sep='\t')
    df_codelist = pd.read_csv(codelist_file, sep='\t', dtype=str)
    df_response = pd.read_csv(response_file, sep='\t')
    
    df_merge = df_question.merge(df_instruction, on='questionLabel', how='left').merge(df_response, on='questionLabel', how='left').merge(df_codelist, on='questionLabel', how='left')
    df_merge['code_list'] = df_merge[['Value', 'Category']].apply(lambda x: ', '.join(x.dropna()), axis=1)
    
    # df_comb = df_merge.groupby('questionLabel')['code_list'].apply('\t '.join).reset_index()
    # df_merge_comb = df_merge.merge(df_comb, on='questionLabel', how='left')
    df_merge = df_merge.drop_duplicates(keep='first')

    df_merge.rename(columns={'questionLabel': 'question_name', 'Instruction': 'instruction', 'Literal': 'question', 'Response': 'response'}, inplace=True)
    
    df_question_m = pd.melt(df_merge, value_vars=['question_name', 'question', 'instruction', 'response', 'code_list'], ignore_index=False).sort_index().drop_duplicates(keep='first')
    df_question_m['value'].replace('', np.nan, inplace=True)
    df_question_m = df_question_m.dropna(subset = ['value'])
    
    # no dup
    df_question_m.rename(columns={'variable': 'item_type', 'value': 'content'}, inplace=True)
    df_question_m = df_question_m.drop_duplicates(keep='first')

    # condition
    df_condition = pd.read_csv(condition_file, sep='\t')
    df_condition['item_type'] = df_condition['Label'].apply(lambda x: 'condition (' + x.split(' ')[0].lower() + ')')
    df_condition['content'] = df_condition['Label']
     
    # loop
    df_loop = pd.read_csv(loop_file, sep='\t')
    df_loop['item_type'] = 'condition (loop)'
    df_loop['content'] = df_loop['Label']
   
  
    #combine
    df_all = df_sequence[['item_type', 'content']].append(df_question_m).append(df_condition[['item_type', 'content']]).append(df_loop[['item_type', 'content']])
    df_all.to_csv(esrc_file, sep='\t', index=False)


if __name__ == "__main__":
    main()

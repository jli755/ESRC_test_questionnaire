#!/bin/env python3

"""  
    Modify the testing data to have same label as training data
    - 'condition (if)',  'condition (elseif)' become 'conditional'
    - 'code_list' become 'codelist'
    - 'question', 'question_name', 'instruction' stay the same
    - no 'statement'
    - 'condition (loop)' become 'loop'
    - remove 'response'
    - what about sequence?? the training data doesn't have it (RCNIC does have it though), will remove it 
"""

from pathlib import Path
import pandas as pd

outdir = '../2021_12_13'
Path(outdir).mkdir(parents=True, exist_ok=True)

# get 3 test files
test_files = list(Path('../questionnaire/').glob('**/*_ESRC.csv'))

for f in test_files:
    df = pd.read_csv(f, sep='\t')
    
    # modify item type
    df['new'] = df['item_type'].apply(lambda x: 'conditional' if x == 'condition (if)' else 
                                                'codelist' if x == 'code_list' else
                                                'loop' if x == 'condition (loop)' else
                                                x)
    # drop column                                            
    df.drop('item_type', axis=1, inplace=True)
    
    # rename column
    df.rename(columns={'new': 'item_type'}, inplace=True)
    
    # re-order columns
    df = df[['item_type', 'content']]
    
    # remove response and sequence
    df_sub = df[~df['item_type'].isin(['response', 'sequence'])]

    df_sub.to_csv(Path(outdir, f.name), sep='\t')


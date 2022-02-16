import argparse
import dsc
import csv
import os
from util import get_encoding_type

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Converts tabulated text from Mettler-Toledo STARe '
        'software to csv.')
    parser.add_argument('file', help='file to convert to csv')
    parser.add_argument('-f', '--force', help='overwrite existing csvs',
        action='store_true')
    args = parser.parse_args()
    data = {}

    new_file_name = os.path.splitext(os.path.abspath(args.file))[0]+'.csv'
    if os.path.exists(new_file_name) and not args.force:
        raise Exception('CSV output file already exists.'
        ' Specify force option to overwrite.')

    with open(args.file,
            encoding = get_encoding_type(args.file)) as f:
        text = f.read()
        data = dsc.parse_tabulated_txt(text)

    with open(new_file_name, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['Index','t','Heatflow','Tr']) # Header
        for i in data.Index:
            #assert(data['Index'][i]==i)
            writer.writerow([data.Index[i],
                data.t[i], data.Heatflow[i], data.Tr[i]])


"""Check bill records for a supplied month; never initiates payments or estimates missing bills."""
import argparse
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
import json
import re

FIELDS = ['bill_id', 'bill', 'due_date', 'amount', 'currency', 'amount_status', 'source_id']

def check(path, month):
    if not re.fullmatch(r'\d{4}-\d{2}', month): raise ValueError('month must be YYYY-MM')
    date.fromisoformat(month + '-01')
    issues = []; seen = set(); totals = {}; outside = []; records = 0
    with open(path, encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream, strict=True)
        if reader.fieldnames != FIELDS: raise ValueError('headers must be exactly: ' + ','.join(FIELDS))
        for n, raw in enumerate(reader, 2):
            records += 1
            if None in raw or any(v is None for v in raw.values()): raise ValueError('wrong number of fields at record ' + str(n))
            row = {k: v.strip() for k,v in raw.items()}; codes = []
            if not row['bill_id']: codes.append('missing_id')
            elif row['bill_id'] in seen: codes.append('duplicate_id')
            seen.add(row['bill_id'])
            for field in ('bill', 'source_id'):
                if not row[field]: codes.append('missing_' + field)
            if not re.fullmatch(r'[A-Z]{3}', row['currency']): codes.append('invalid_currency_format')
            if row['amount_status'] not in ('actual', 'estimate'): codes.append('invalid_amount_status')
            try:
                if not re.fullmatch(r'\d{1,12}(\.\d{1,2})?', row['amount']): raise InvalidOperation
                amount = Decimal(row['amount'])
                if not amount.is_finite(): raise InvalidOperation
            except InvalidOperation: codes.append('invalid_amount')
            due = None
            try:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', row['due_date']): raise ValueError()
                due = date.fromisoformat(row['due_date'])
            except ValueError: codes.append('invalid_due_date')
            if codes: issues.append({'record': n, 'bill_id': row['bill_id'], 'issues': codes})
            elif due.strftime('%Y-%m') != month: outside.append({'bill_id':row['bill_id'], 'due_date':row['due_date']})
            else:
                key = (row['currency'],row['amount_status'])
                totals[key] = totals.get(key,Decimal('0')) + amount
    if not records: raise ValueError('no data records')
    # Totals are withheld whenever a malformed or duplicated record exists.
    return {'month':month,'records':records,'totals_withheld':bool(issues),'totals':[] if issues else [{'currency':k[0],'amount_status':k[1],'amount':format(v,'.2f')} for k,v in sorted(totals.items())], 'outside_month':outside,'issues':issues,'coverage_proven':False}

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('csv_file'); p.add_argument('--month',required=True); args=p.parse_args()
    try: result=check(args.csv_file,args.month)
    except (ValueError,OSError,csv.Error) as error: p.exit(2,'Input error: '+str(error)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

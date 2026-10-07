import polars as pl
import xml.etree.ElementTree as ET
from lxml import etree
from lxml.cssselect import CSSSelector

def strip_namespaces(root):
    for elem in root.iter():
        if isinstance(elem.tag, str):
            elem.tag = etree.QName(elem).localname
    return root

def load_saft_as_xml(path: str):
    tree = etree.parse(path)
    root = tree.getroot()
    root = strip_namespaces(root)

    return root

def extract_header(root):
    return pl.DataFrame({
        "AuditFileVersion": [CSSSelector("Header > AuditFileVersion")(root)[0].text],
        "CompanyID": [CSSSelector("Header > CompanyID")(root)[0].text],
        "TaxRegistrationNumber": [CSSSelector("Header > TaxRegistrationNumber")(root)[0].text],
        "TaxAccountingBasis": [CSSSelector("Header > TaxAccountingBasis")(root)[0].text],
        "CompanyName": [CSSSelector("Header > CompanyName")(root)[0].text],
        "BusinessName": [CSSSelector("Header > BusinessName")(root)[0].text],
        "FiscalYear": [CSSSelector("Header > FiscalYear")(root)[0].text],
        "AddressDetail": [CSSSelector("Header > CompanyAddress > AddressDetail")(root)[0].text],
        "City": [CSSSelector("Header > CompanyAddress > City")(root)[0].text],
        "PostalCode": [CSSSelector("Header > CompanyAddress > PostalCode")(root)[0].text],
        "Country": [CSSSelector("Header > CompanyAddress > Country")(root)[0].text],
        "StartDate": [CSSSelector("Header > StartDate")(root)[0].text],
        "EndDate": [CSSSelector("Header > EndDate")(root)[0].text],
        "CurrencyCode": [CSSSelector("Header > CurrencyCode")(root)[0].text],
        "DateCreated": [CSSSelector("Header > DateCreated")(root)[0].text],
        "TaxEntity": [CSSSelector("Header > TaxEntity")(root)[0].text],
        "ProductCompanyTaxID": [CSSSelector("Header > ProductCompanyTaxID")(root)[0].text],
        "SoftwareCertificateNumber": [CSSSelector("Header > SoftwareCertificateNumber")(root)[0].text],
        "ProductID": [CSSSelector("Header > ProductID")(root)[0].text],
        "ProductVersion": [CSSSelector("Header > ProductVersion")(root)[0].text],
    })

def extract_costumers(root):
    costumers = CSSSelector("MasterFiles > Customer")(root)

    data = {
        "CustomerID": [],
        "AccountID": [],
        "CustomerTaxID": [],
        "BillingAddress_AddressDetail": [],
        "BillingAddress_City": [],
        "BillingAddress_PostalCode": [],
        "BillingAddress_Country": [],

        "ShipToAddress_AddressDetail": [],
        "ShipToAddress_City": [],
        "ShipToAddress_PostalCode": [],
        "ShipToAddress_Country": [],

        "SelfBillingIndicator": [],
        "Telephone": [],
        "Email": []
    }
    
    for costumer in costumers:
        data["CustomerID"].append(CSSSelector("CustomerID")(costumer)[0].text)
        data["AccountID"].append(CSSSelector("AccountID")(costumer)[0].text)
        data["CustomerTaxID"].append(CSSSelector("CustomerTaxID")(costumer)[0].text)
        data["BillingAddress_AddressDetail"].append(CSSSelector("BillingAddress > AddressDetail")(costumer)[0].text)
        data["BillingAddress_City"].append(CSSSelector("BillingAddress > City")(costumer)[0].text)
        data["BillingAddress_PostalCode"].append(CSSSelector("BillingAddress > PostalCode")(costumer)[0].text)
        data["BillingAddress_Country"].append(CSSSelector("BillingAddress > Country")(costumer)[0].text)

        data["ShipToAddress_AddressDetail"].append(CSSSelector("ShipToAddress > AddressDetail")(costumer)[0].text)
        data["ShipToAddress_City"].append(CSSSelector("ShipToAddress > City")(costumer)[0].text)
        data["ShipToAddress_PostalCode"].append(CSSSelector("ShipToAddress > PostalCode")(costumer)[0].text)
        data["ShipToAddress_Country"].append(CSSSelector("ShipToAddress > Country")(costumer)[0].text)

        data["SelfBillingIndicator"].append(CSSSelector("SelfBillingIndicator")(costumer)[0].text)

        if CSSSelector("Telephone")(costumer):
            data["Telephone"].append(CSSSelector("Telephone")(costumer)[0].text)
        else:
            data["Telephone"].append("")

        if CSSSelector("Email")(costumer):
            data["Email"].append(CSSSelector("Email")(costumer)[0].text)
        else:
            data["Email"].append("")
    
    return pl.DataFrame(data)

def extract_products(root):
    products = CSSSelector("MasterFiles > Product")(root)

    data = {
        "ProductType": [],
        "ProductCode": [],
        "ProductGroup": [],
        "ProductDescription": [],
        "ProductNumberCode": [],
        "CustomsDetails_UNNumber": []
    }
    
    for product in products:
        data["ProductType"].append(CSSSelector("ProductType")(product)[0].text)
        data["ProductCode"].append(CSSSelector("ProductCode")(product)[0].text)
        data["ProductGroup"].append(CSSSelector("ProductGroup")(product)[0].text)
        data["ProductDescription"].append(CSSSelector("ProductDescription")(product)[0].text)
        data["ProductNumberCode"].append(CSSSelector("ProductNumberCode")(product)[0].text)

        if CSSSelector("CustomsDetails > UNNumber")(product):
            data["CustomsDetails_UNNumber"].append(CSSSelector("CustomsDetails > UNNumber")(product)[0].text)
        else:
            data["CustomsDetails_UNNumber"].append("")
        
    return pl.DataFrame(data)

def extract_tax_table(root):
    rows = CSSSelector("MasterFiles > TaxTable > TaxTableEntry")(root)
    
    data = {
        "TaxType": [],
        "TaxCountryRegion":[ ],
        "TaxCode":[],
        "Description":[],
        "TaxPercentage":[],
    }
    
    for row in rows:
        data["TaxType"].append(CSSSelector("TaxType")(row)[0].text)
        data["TaxCountryRegion"].append(CSSSelector("TaxCountryRegion")(row)[0].text)
        data["TaxCode"].append(CSSSelector("TaxCode")(row)[0].text)
        data["Description"].append(CSSSelector("Description")(row)[0].text)
        data["TaxPercentage"].append(CSSSelector("TaxPercentage")(row)[0].text)
    
    return pl.DataFrame(data)

def extract_sales_invoices(root):
    rows = CSSSelector("SourceDocuments > SalesInvoices")(root)
    
    data = {
        "NumberOfEntries": [],
        "TotalDebit": [],
        "TotalCredit": []
    }
    
    for row in rows:
        data["NumberOfEntries"].append(CSSSelector("NumberOfEntries")(row)[0].text)
        data["TotalDebit"].append(CSSSelector("TotalDebit")(row)[0].text)
        data["TotalCredit"].append(CSSSelector("TotalCredit")(row)[0].text)
    
    return pl.DataFrame(data)

def extract_invoices(root):
    rows = CSSSelector("SourceDocuments > SalesInvoices > Invoice")(root)
    
    data = {
        "InvoiceNo": [],
        "ATCUD": [],
        "InvoiceStatus": [],
        "InvoiceStatusDate": [],
        "SourceID": [],
        "SourceBilling": [],
        "Hash": [],
        "HashControl": [],
        "Period": [],
        "InvoiceDate": [],
        "InvoiceType": [],
        "CashVATSchemeIndicator": [],
        "ThirdPartiesBillingIndicator": [],
        "SystemEntryDate": [],
        "TaxPayable": [],
        "NetTotal": [],
        "GrossTotal": [],
        "SettlementDate": [],
        "PaymentTerms": [],
        "DebitAmount": [],
        "PaymentMechanism": [],
        "PaymentAmount": [],
        "PaymentDate": [],
        "SettlementAmount": [],
        "Reason": []
    }

    data_line = {
        "invoice_n": [],
        "LineNumber": [],
        "Quantity": [],
        "UnitOfMeasure": [],
        "UnitPrice": [],
        "TaxPointDate": [],
        "CreditAmount": [],
        "TaxType": [],
        "TaxCountryRegion": [],
        "TaxCode": [],
        "TaxPercentage": [],
        "TaxBase": [],
        "TaxExemptionReason": [],
        "TaxExemptionCode": []
    }
    
    
    for row in rows:
        invoice_n = CSSSelector("InvoiceNo")(row)[0].text
        
        data["InvoiceNo"].append(invoice_n)
        data["ATCUD"].append(CSSSelector("ATCUD")(row)[0].text)
        data["InvoiceStatus"].append(CSSSelector("DocumentStatus > InvoiceStatus")(row)[0].text)
        data["InvoiceStatusDate"].append(CSSSelector("DocumentStatus > InvoiceStatusDate")(row)[0].text)
        data["SourceID"].append(CSSSelector("DocumentStatus > SourceID")(row)[0].text)
        data["SourceBilling"].append(CSSSelector("DocumentStatus > SourceBilling")(row)[0].text)
        data["Hash"].append(CSSSelector("Hash")(row)[0].text)
        data["HashControl"].append(CSSSelector("HashControl")(row)[0].text)
        data["Period"].append(CSSSelector("Period")(row)[0].text)
        data["InvoiceDate"].append(CSSSelector("InvoiceDate")(row)[0].text)
        data["InvoiceType"].append(CSSSelector("InvoiceType")(row)[0].text)

        data["CashVATSchemeIndicator"].append(CSSSelector("SpecialRegimes > CashVATSchemeIndicator")(row)[0].text)
        data["ThirdPartiesBillingIndicator"].append(CSSSelector("SpecialRegimes > ThirdPartiesBillingIndicator")(row)[0].text)

        data["SystemEntryDate"].append(CSSSelector("SystemEntryDate")(row)[0].text)

        data["TaxPayable"].append(CSSSelector("DocumentTotals > TaxPayable")(row)[0].text)
        data["NetTotal"].append(CSSSelector("DocumentTotals > NetTotal")(row)[0].text)
        data["GrossTotal"].append(CSSSelector("DocumentTotals > GrossTotal")(row)[0].text)
        data["SettlementDate"].append(CSSSelector("Settlement > SettlementDate")(row)[0].text)
        data["PaymentTerms"].append(CSSSelector("Settlement > PaymentTerms")(row)[0].text)

        if CSSSelector("SettlementAmount")(row):
            data["SettlementAmount"].append(CSSSelector("SettlementAmount")(row)[0].text)
        else:
            data["SettlementAmount"].append("")

        if CSSSelector("Reason")(row):
            data["Reason"].append(CSSSelector("Reason")(row)[0].text)
        else:
            data["Reason"].append("")
        
        if CSSSelector("Payment > PaymentMechanism")(row):
            data["PaymentMechanism"].append(CSSSelector("Payment > PaymentMechanism")(row)[0].text)
        else:
            data["PaymentMechanism"].append("")

        if CSSSelector("Payment > PaymentAmount")(row):
            data["PaymentAmount"].append(CSSSelector("Payment > PaymentAmount")(row)[0].text)
        else:
            data["PaymentAmount"].append("")

        if CSSSelector("Payment > PaymentDate")(row):
            data["PaymentDate"].append(CSSSelector("Payment > PaymentDate")(row)[0].text)
        else:
            data["PaymentDate"].append("")
        
        
        if CSSSelector("DebitAmount")(row):
            data["DebitAmount"].append(CSSSelector("DebitAmount")(row)[0].text)
        else:
            data["DebitAmount"].append("")

        
        for line in CSSSelector("Line")(row):
            data_line["invoice_n"].append(invoice_n)
            data_line["LineNumber"].append(CSSSelector("LineNumber")(line)[0].text)
            data_line["Quantity"].append(CSSSelector("Quantity")(line)[0].text)
            data_line["UnitOfMeasure"].append(CSSSelector("UnitOfMeasure")(line)[0].text)
            data_line["UnitPrice"].append(CSSSelector("UnitPrice")(line)[0].text)
            data_line["TaxPointDate"].append(CSSSelector("TaxPointDate")(line)[0].text)

            data_line["TaxType"].append(CSSSelector("Tax > TaxType")(line)[0].text)
            data_line["TaxCountryRegion"].append(CSSSelector("Tax > TaxCountryRegion")(line)[0].text)
            data_line["TaxCode"].append(CSSSelector("Tax > TaxCode")(line)[0].text)
            data_line["TaxPercentage"].append(CSSSelector("Tax > TaxPercentage")(line)[0].text)

            if CSSSelector("TaxBase")(line):
                data_line["TaxBase"].append(CSSSelector("TaxBase")(line)[0].text)
            else:
                data_line["TaxBase"].append("") 


            if CSSSelector("TaxExemptionReason")(line):
                data_line["TaxExemptionReason"].append(CSSSelector("TaxExemptionReason")(line)[0].text)
            else:
                data_line["TaxExemptionReason"].append("") 

            if CSSSelector("TaxExemptionCode")(line):
                data_line["TaxExemptionCode"].append(CSSSelector("TaxExemptionCode")(line)[0].text)
            else:
                data_line["TaxExemptionCode"].append("") 

                
            if CSSSelector("CreditAmount")(line):
                data_line["CreditAmount"].append(CSSSelector("CreditAmount")(line)[0].text)
            else:
                data_line["CreditAmount"].append("")            
    
    return pl.DataFrame(data), pl.DataFrame(data_line)

def extract_work_document(root):
    rows = CSSSelector("WorkingDocuments > WorkDocument")(root)
    
    data = {
        "DocumentNumber": [],
        "ATCUD": [],
        "WorkStatus": [],
        "WorkStatusDate": [],
        "WorkDate": [],
        "WorkType": [],
        "SourceID": [],
        "SourceBilling": [],
        "Hash": [],
        "HashControl": [],
        "SystemEntryDate": [],
        "CustomerID": [],
        "TaxPayable": [],
        "NetTotal": [],
        "GrossTotal": []
    }

    data_line = {
        "doc_number": [],
        "LineNumber": [],
        "ProductCode": [],
        "ProductDescription": [],
        "Quantity": [],
        "UnitOfMeasure": [],
        "UnitPrice": [],
        "TaxPointDate": [],
        "Description": [],
        "CreditAmount": [],
        "TaxType": [],
        "TaxCountryRegion": [],
        "TaxCode": [],
        "TaxPercentage": [],
        "SettlementAmount": []
    }
    
    for row in rows:
        doc_n = CSSSelector("DocumentNumber")(row)[0].text
        
        data["DocumentNumber"].append(doc_n)
        data["WorkStatus"].append(CSSSelector("WorkStatus")(row)[0].text)
        data["WorkStatusDate"].append(CSSSelector("WorkStatusDate")(row)[0].text)
        data["WorkDate"].append(CSSSelector("WorkDate")(row)[0].text)
        data["WorkType"].append(CSSSelector("WorkType")(row)[0].text)
        data["ATCUD"].append(CSSSelector("ATCUD")(row)[0].text)
        data["SourceID"].append(CSSSelector("DocumentStatus > SourceID")(row)[0].text)
        data["SourceBilling"].append(CSSSelector("DocumentStatus > SourceBilling")(row)[0].text)
        data["Hash"].append(CSSSelector("Hash")(row)[0].text)
        data["HashControl"].append(CSSSelector("HashControl")(row)[0].text)
        data["SystemEntryDate"].append(CSSSelector("SystemEntryDate")(row)[0].text)
        data["CustomerID"].append(CSSSelector("CustomerID")(row)[0].text)

        data["TaxPayable"].append(CSSSelector("DocumentTotals > TaxPayable")(row)[0].text)
        data["NetTotal"].append(CSSSelector("DocumentTotals > NetTotal")(row)[0].text)
        data["GrossTotal"].append(CSSSelector("DocumentTotals > GrossTotal")(row)[0].text)

        for line in CSSSelector("Line")(row):
            data_line["doc_number"].append(doc_n)
            data_line["LineNumber"].append(CSSSelector("LineNumber")(line)[0].text)
            data_line["ProductCode"].append(CSSSelector("ProductCode")(line)[0].text)
            data_line["ProductDescription"].append(CSSSelector("ProductDescription")(line)[0].text)
            data_line["Quantity"].append(CSSSelector("Quantity")(line)[0].text)
            data_line["UnitOfMeasure"].append(CSSSelector("UnitOfMeasure")(line)[0].text)
            data_line["UnitPrice"].append(CSSSelector("UnitPrice")(line)[0].text)
            data_line["TaxPointDate"].append(CSSSelector("TaxPointDate")(line)[0].text)
            data_line["Description"].append(CSSSelector("Description")(line)[0].text)
            data_line["CreditAmount"].append(CSSSelector("CreditAmount")(line)[0].text)
            data_line["TaxType"].append(CSSSelector("Tax > TaxType")(line)[0].text)
            data_line["TaxCountryRegion"].append(CSSSelector("Tax > TaxCountryRegion")(line)[0].text)
            data_line["TaxCode"].append(CSSSelector("Tax > TaxCode")(line)[0].text)
            data_line["TaxPercentage"].append(CSSSelector("Tax > TaxPercentage")(line)[0].text)

            if CSSSelector("SettlementAmount")(line):
                data_line["SettlementAmount"].append(CSSSelector("SettlementAmount")(line)[0].text)
            else:
                data_line["SettlementAmount"].append("")
        
    return pl.DataFrame(data), pl.DataFrame(data_line)

def extract_payments(root):
    rows = CSSSelector("Payments")(root)
    
    data = {
        "NumberOfEntries": [],
        "TotalDebit": [],
        "TotalCredit": []
    }
    
    for row in rows:
        data["NumberOfEntries"].append(CSSSelector("NumberOfEntries")(row)[0].text)
        data["TotalDebit"].append(CSSSelector("TotalDebit")(row)[0].text)
        data["TotalCredit"].append(CSSSelector("TotalCredit")(row)[0].text)


    data_payment = {
        "PaymentRefNo": [],
        "ATCUD": [],
        "Period": [],
        "TransactionDate": [],
        "PaymentType": [],
        "PaymentStatus": [],
        "PaymentStatusDate": [],
        "SourceID": [],
        "SourcePayment": [],

        "PaymentMechanism": [],
        "PaymentAmount": [],
        "PaymentDate": [],

        "SystemEntryDate": [],
        "CustomerID": []
    }

    data_payment_lines = {
        "payment_ref_n": [],
        "LineNumber": [],
        "OriginatingON": [],
        "InvoiceDate": [],
        "SettlementAmount": [],
        "CreditAmount": []
    }

    for row in CSSSelector("Payments > Payment")(root):
        payment_ref_n = CSSSelector("PaymentRefNo")(row)[0].text
            
        data_payment["PaymentRefNo"].append(payment_ref_n)
        data_payment["ATCUD"].append(CSSSelector("ATCUD")(row)[0].text)
        data_payment["TransactionDate"].append(CSSSelector("TransactionDate")(row)[0].text)
        data_payment["Period"].append(CSSSelector("Period")(row)[0].text)
        data_payment["PaymentType"].append(CSSSelector("PaymentType")(row)[0].text)

        data_payment["PaymentStatus"].append(CSSSelector("DocumentStatus > PaymentStatus")(row)[0].text)
        data_payment["PaymentStatusDate"].append(CSSSelector("DocumentStatus > PaymentStatusDate")(row)[0].text)
        data_payment["SourceID"].append(CSSSelector("DocumentStatus > SourceID")(row)[0].text)
        data_payment["SourcePayment"].append(CSSSelector("DocumentStatus > SourcePayment")(row)[0].text)

        if CSSSelector("PaymentMechanism")(row):
            data_payment["PaymentMechanism"].append(CSSSelector("PaymentMethod > PaymentMechanism")(row)[0].text)
        else:
            data_payment["PaymentMechanism"].append("")

        if CSSSelector("PaymentAmount")(row):
            data_payment["PaymentAmount"].append(CSSSelector("PaymentMethod > PaymentAmount")(row)[0].text)
        else:
            data_payment["PaymentAmount"].append("")

        if CSSSelector("PaymentDate")(row):
            data_payment["PaymentDate"].append(CSSSelector("PaymentMethod > PaymentDate")(row)[0].text)
        else:
            data_payment["PaymentDate"].append("")

        data_payment["SystemEntryDate"].append(CSSSelector("SystemEntryDate")(row)[0].text)
        data_payment["CustomerID"].append(CSSSelector("CustomerID")(row)[0].text)

        for line in CSSSelector("Line")(row):
            data_payment_lines["payment_ref_n"].append(payment_ref_n)
            data_payment_lines["LineNumber"].append(CSSSelector("LineNumber")(row)[0].text)
            data_payment_lines["OriginatingON"].append(CSSSelector("SourceDocumentID > OriginatingON")(row)[0].text)
            data_payment_lines["InvoiceDate"].append(CSSSelector("SourceDocumentID > InvoiceDate")(row)[0].text)

            data_payment_lines["SettlementAmount"].append(CSSSelector("SettlementAmount")(row)[0].text)
            data_payment_lines["CreditAmount"].append(CSSSelector("CreditAmount")(row)[0].text)

        
    return pl.DataFrame(data), pl.DataFrame(data_payment), pl.DataFrame(data_payment_lines) 

__all__ = ["load_saft_as_xml", "extract_header", "extract_costumers", "extract_products", "extract_tax_table", "extract_sales_invoices", "extract_invoices", "extract_work_document", "extract_payments"]
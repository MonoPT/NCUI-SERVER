from pprint import pprint
from node import Node, NodeOutput, Output, get_connect_value_by_input_handle_name

from .utils import load_saft_as_xml, extract_header, extract_costumers, extract_products, extract_tax_table, extract_sales_invoices, extract_invoices, extract_work_document, extract_payments

from state import GlobalState

from fs import load_asset

def func(node: dict, predecessors: list[tuple[dict, dict]], gs: GlobalState) -> NodeOutput:
    
    input_str: str | None = get_connect_value_by_input_handle_name("string_input", predecessors)
    
    data = node["data"]

    if not input_str:
        path: str | None = None
        
        if (len(data["files"]) > 0):
            file = data["files"][0]
            
            path = str(file["path"])
        
            input_str = str(path) if path is not None else None
    
    if not input_str or len(input_str.strip()) < 1:
        raise FileNotFoundError(f"Input path {input_str} is not valid")

    file_path = load_asset(input_str)

    if not input_str:
        raise FileNotFoundError(f"Input path {file_path} is not valid")
    
    root = load_saft_as_xml(str(file_path))

    header = extract_header(root)
    costumers = extract_costumers(root)
    products = extract_products(root)
    tax = extract_tax_table(root)
    invoices_meta = extract_sales_invoices(root)
    invoices, invoices_lines = extract_invoices(root)
    work_document, work_document_lines = extract_work_document(root)
    payments_meta, payments, payments_lines= extract_payments(root)
    
    
    return NodeOutput(id=node["id"], outputs=[
        Output(handle="df_header", value=header.lazy()),
        Output(handle="df_costumers", value=costumers.lazy()),
        Output(handle="df_products", value=products.lazy()),
        Output(handle="df_tax", value=tax.lazy()),
        Output(handle="df_invoices_meta", value=invoices_meta.lazy()),
        Output(handle="df_invoices", value=invoices.lazy()),
        Output(handle="df_invoices_lines", value=invoices_lines.lazy()),
        Output(handle="df_work_document", value=work_document.lazy()),
        Output(handle="df_work_document_lines", value=work_document_lines.lazy()),
        Output(handle="df_payments_meta", value=payments_meta.lazy()),
        Output(handle="df_payments", value=payments.lazy()),
        Output(handle="df_payments_lines", value=payments_lines.lazy()),
    ])

class LoadSaft(Node):
    def __init__(self):
        identifier = "loadSAFT"
        author = "MonoPT"
        namespace = "core"
        version = "1.0"
        group = "dataframe"
        fn = func
        namespace = namespace
                
        super().__init__(identifier, author, version, group, namespace, fn)
        
__all__ = ["LoadSaft"]
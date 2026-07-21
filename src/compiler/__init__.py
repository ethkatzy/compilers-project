from tokenizer import tokenize
from parser import parse
from ir_generator import GLOBAL_SYMTAB, generate_ir
from assembly_generator import generate_assembly

source_code = """if true then { print_int(2); } else { print_int(3); }"""
tokens = tokenize(source_code)
parsed = parse(tokens)
ir_lines = generate_ir(GLOBAL_SYMTAB, parsed)
assembly = generate_assembly(ir_lines)
print(assembly)
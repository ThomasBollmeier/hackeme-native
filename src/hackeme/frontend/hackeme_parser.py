from .hackeme_base_parser import HackemeBaseParser
from komparse import Ast


class HackemeParser(HackemeBaseParser):

    def __init__(self):
        HackemeBaseParser.__init__(self)
        self._init_transformations()

    def parse(self, source):
        ast = HackemeBaseParser.parse(self, source)
        if ast:
            arity_grouping = _ArityGrouping()
            ast.walk(arity_grouping)
            return arity_grouping.get_grouped_ast()
        else:
            return None

    def _init_transformations(self):
        g = self._grammar        
        g.set_ast_transform('start', self._start)
        g.set_ast_transform('definition', lambda ast: ast.get_children()[0])
        g.set_ast_transform('vardef', self._vardef)
        g.set_ast_transform('fundef', self._fundef)
        g.set_ast_transform('expr', lambda ast: ast.get_children()[0])
        g.set_ast_transform('no_list', lambda ast: ast.get_children()[0])
        g.set_ast_transform('if_expr', self._if_expr)
        g.set_ast_transform('cond_expr', self._cond_expr)
        g.set_ast_transform('cond_branch', self._cond_branch)
        g.set_ast_transform('call', self._call)
        g.set_ast_transform('operator', self._operator)
        g.set_ast_transform('boolean', self._boolean)
        g.set_ast_transform('list', self._list)
        g.set_ast_transform('list_item', self._list_item)
        
    # AST transformations:

    @staticmethod
    def _start(ast):
        ret = Ast('hackeme')
        for child in ast.get_children():
            child.id = ''
            ret.add_child(child)
        return ret
    
    @staticmethod
    def _vardef(ast):
        ret = Ast('vardef')
        name_node = ast.find_children_by_id('name')[0]
        ret.set_attr('name', name_node.value)
        ret.add_children_by_id(ast, 'value')
        return ret
    
    @staticmethod
    def _fundef(ast):
        ret = Ast('fundef')
        name_node = ast.find_children_by_id('name')[0]
        ret.set_attr('name', name_node.value)
        params = Ast('parameters')
        ret.add_child(params)
        param_nodes = ast.find_children_by_id('param')
        for param_node in param_nodes:
            params.add_child(Ast('parameter', param_node.value))
        vararg = ast.find_children_by_id('vararg')
        if vararg:
            vararg = vararg[0]
            params.add_child(Ast('var', vararg.value[:-1]))
        localdefs = Ast('localdefs')
        ret.add_child(localdefs)
        localdefs.add_children_by_id(ast, 'localdef')
        body = Ast('body')
        ret.add_child(body)
        body.add_children_by_id(ast, 'body')
        return ret
    
    @staticmethod
    def _if_expr(ast):
        ret = Ast('if_expr')
        test = Ast('test')
        ret.add_child(test)
        test.add_children_by_id(ast, 'test')
        consequent = Ast('consequent')
        ret.add_child(consequent)
        consequent.add_children_by_id(ast, 'consequent')
        alternate = Ast('alternate')
        ret.add_child(alternate)
        alternate.add_children_by_id(ast, 'alternate')
        return ret
    
    @staticmethod
    def _cond_expr(ast):
        ret = Ast('cond')
        ret.add_children_by_id(ast, 'branch')
        return ret
    
    @staticmethod
    def _cond_branch(ast):
        ret = Ast('branch')
        test = Ast('test')
        ret.add_child(test)
        test.add_children_by_id(ast, 'test')
        consequent = Ast('consequent')
        ret.add_child(consequent)
        consequent.add_children_by_id(ast, 'consequent')
        return ret
    
    @staticmethod
    def _call(ast):
        ret = Ast('call')
        callee = Ast('callee')
        ret.add_child(callee)
        callee.add_children_by_id(ast, 'callee')
        args = Ast('arguments')
        ret.add_child(args)
        args.add_children_by_id(ast, 'arg')
        return ret
    
    @staticmethod
    def _operator(ast):
        ret = Ast('operator')
        op = ast.get_children()[0].value
        ret.set_attr('value', op)
        return ret
    
    @staticmethod
    def _boolean(ast):
        child = ast.get_children()[0]
        if child.value == '#t' or child.value == '#true':
            return Ast('TRUE')
        else:
            return Ast('FALSE')
        
    @staticmethod
    def _list(ast):
        ret = Ast('list')
        ret.add_children_by_id(ast, 'li')
        return ret
    
    @staticmethod
    def _list_item(ast):
        children = ast.find_children_by_id('single')
        if children:
            ret = children[0]
            ret.id = ''
            return ret
        else:
            ret = Ast('list')
            ret.add_children_by_id(ast, 'li')
            return ret

class _ArityGrouping(object):
    """
    Group arities into function definition node
    """
    def __init__(self):
        self._ast = None
        self._node_stack = []
        self._func_stack = []
        
    def get_grouped_ast(self):
        return self._ast
    
    def enter_node(self, node):
        
        if node.has_attr('root'):
        
            self._ast = node.copy()
            self._node_stack.append(self._ast)
            self._func_stack = [{}]
            
        elif node.name == 'fundef':
            
            arity = Ast("arity")
            
            func_name = node.get_attr('name')
            funcs = self._func_stack[-1]
            if func_name not in funcs:
                func_node = node.copy()
                funcs[func_name] = func_node
                self._add_to_parent(func_node)
            else:
                func_node = funcs[func_name]
                
            func_node.add_child(arity)
            self._node_stack.append(arity)
            
            self._func_stack.append({})
                
        else:
            self._node_stack.append(node.copy())
            
    def exit_node(self, node):
        child = self._node_stack.pop()
        if node.name != "fundef":
            self._add_to_parent(child)
        else:
            self._func_stack.pop()
        
    def visit_node(self, node):
        self._add_to_parent(node.copy())
            
    def _add_to_parent(self, node):
        if self._node_stack:
            parent = self._node_stack[-1]
            parent.add_child(node)

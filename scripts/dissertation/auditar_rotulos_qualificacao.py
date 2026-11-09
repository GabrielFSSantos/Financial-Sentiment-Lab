"""Recalcula somente diagnósticos dos rótulos preservados; não executa inferência."""
from pathlib import Path
import ast
import hashlib
import json
import re
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, cohen_kappa_score

root = Path(__file__).resolve().parents[2]
source = root / 'data/water_utilities_corpus/manual_labels_100_eval.csv'
frame = pd.read_csv(source)
labels = ['NEG', 'NEU', 'POS']
assert len(frame) == 100 and frame['id'].nunique() == 100
assert frame[['rotulo_manual', 'rotulo_finbert']].notna().all().all()
assert set(frame.rotulo_manual).issubset(labels)
assert set(frame.rotulo_finbert).issubset(labels)

# Extrai apenas a constante e a função pura, sem importar o módulo que prepara dados.
tree = ast.parse((root / 'modules/evaluation/classifier_error_analysis.py').read_text())
nodes = [node for node in tree.body if
    isinstance(node, ast.AnnAssign) and getattr(node.target, 'id', '') == 'ROUNDUP_PATTERNS'
    or isinstance(node, ast.FunctionDef) and node.name == 'classify_typology']
assert len(nodes) == 2
namespace = {'pd': pd, 're': re}
exec(compile(ast.Module(body=nodes, type_ignores=[]), 'heuristica_preservada', 'exec'), namespace)
frame['tipologia_heuristica'] = frame.apply(namespace['classify_typology'], axis=1)
matrix = confusion_matrix(frame.rotulo_manual, frame.rotulo_finbert, labels=labels)
assert matrix.tolist() == [[13, 1, 0], [21, 32, 14], [4, 10, 5]], 'CSV diverge da revisão: não alterar números silenciosamente.'
report = classification_report(frame.rotulo_manual, frame.rotulo_finbert, labels=labels,
                               output_dict=True, zero_division=0)
kappa = cohen_kappa_score(frame.rotulo_manual, frame.rotulo_finbert, labels=labels)
assert abs(report['accuracy'] - .5) < 1e-12
assert abs(kappa - .1969161580469002) < 1e-12
assert frame.tipologia_heuristica.value_counts().to_dict() == {'focal_sabesp': 74, 'roundup_agenda': 26}
subsets = {}
for name, group in frame.groupby('tipologia_heuristica'):
    subsets[name] = {'n': len(group),
        'kappa': cohen_kappa_score(group.rotulo_manual, group.rotulo_finbert, labels=labels),
        'report': classification_report(group.rotulo_manual, group.rotulo_finbert,
                                        labels=labels, output_dict=True, zero_division=0)}
out = root / 'docs/Dissertacao_PPGCC/generated/auditoria_qualificacao'
out.mkdir(parents=True, exist_ok=True)
payload = {'source': str(source.relative_to(root)), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
           'labels_order': labels, 'confusion_matrix': matrix.tolist(), 'kappa': kappa,
           'report': report, 'subsets': subsets, 'new_inference': False,
           'probabilities_available_in_source': False,
           'representation': 'titulo e corpo, conforme protocolo documentado; entrada tokenizada não disponível'}
(out / 'metricas_100.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
inventory = frame[['id', 'data', 'fonte', 'url', 'rotulo_manual', 'rotulo_finbert', 'tipologia_heuristica']].copy()
for col in ['p_positivo', 'p_negativo', 'p_neutro']:
    inventory[col] = pd.NA
inventory['status_probabilidades'] = 'não disponíveis no CSV consultado; não reinferidas'
inventory.to_csv(out / 'inventario_100.csv', index=False)
print('100 itens; matriz e métricas conferidas; probabilidades ausentes explicitadas; sem nova inferência.')

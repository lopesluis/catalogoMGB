from enum import Enum

class StatusMetadado(Enum):
    PENDENTE = 'pendente'
    APROVADO = 'aprovado'
    REJEITADO = 'rejeitado'
    RASCUNHO = 'rascunho'

class Workflow:
    """Define as transições possíveis do workflow"""
    
    TRANSICOES = {
        StatusMetadado.RASCUNHO: [StatusMetadado.PENDENTE],
        StatusMetadado.PENDENTE: [StatusMetadado.APROVADO, StatusMetadado.REJEITADO],
        StatusMetadado.APROVADO: [StatusMetadado.PENDENTE],  # Pode voltar para revisão
        StatusMetadado.REJEITADO: [StatusMetadado.PENDENTE]  # Pode ser reenviado
    }
    
    @staticmethod
    def pode_transitar(status_atual, status_novo):
        return status_novo in Workflow.TRANSICOES.get(status_atual, [])
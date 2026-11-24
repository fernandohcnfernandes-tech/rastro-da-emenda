export type Status = "verde" | "amarelo" | "laranja" | "vermelho" | "azul" | "cinza";

export interface EmendaResumo {
  id_plano_acao: number;
  codigo_plano_acao: string;
  emenda_numero: string | null;
  ano: number | null;
  parlamentar: string | null;
  beneficiario: string | null;
  uf: string | null;
  codigo_ibge: string | null;
  municipio: string | null;
  populacao: number | null;
  valor_previsto: number | null;
  repassado: number | null;
  primeiro_pagamento: string | null;
  status: Status;
  alertas: string[];
  objeto: string | null;
}

export interface ListaEmendas {
  total: number;
  pagina: number;
  tamanho: number;
  itens: EmendaResumo[];
  resumo_status: Partial<Record<Status, number>>;
}

export interface Evento {
  etapa: "indicacao" | "plano_trabalho" | "pagamento" | "licitacao" | "contrato";
  data: string;
  titulo: string;
  descricao?: string;
  valor?: number | null;
  url?: string | null;
  data_aproximada?: boolean;
}

export interface EvidenciaFicha {
  id: number;
  fonte: string;
  data_publicacao: string | null;
  data_assinatura: string | null;
  objeto: string | null;
  valor: number | null;
  modalidade: string | null;
  tipo_ato: string | null;
  situacao: string | null;
  fornecedor_documento: string | null;
  fornecedor_nome: string | null;
  url: string | null;
  trecho: string | null;
  compativel: boolean;
  confianca: number;
  metodo: string | null;
  justificativa_ia: string | null;
  trechos_citados: string[] | null;
  conta_como_evidencia: boolean;
}

export interface ExecucaoContabil {
  data_referencia: string;
  recebido: number;
  recebido_ate_corte: number;
  receita_fonte_706: number;
  empenhado: number;
  preempenhado?: number;
  bloqueado?: number;
  pago: number;
  usa_fonte: boolean;
  fracao_empenhada: number | null;
}

export interface Ficha extends EmendaResumo {
  detalhes: { contabil?: ExecucaoContabil | null } | null;
  situacao: string | null;
  valor_custeio: number | null;
  valor_investimento: number | null;
  objeto_completo: string | null;
  esfera: string | null;
  obrigado_pncp: boolean | null;
  coberto_querido_diario: boolean | null;
  justificativa: string | null;
  avaliado_em: string | null;
  alertas_detalhados: { codigo: string; descricao: string }[];
  emenda_portal: { autor: string; valor_empenhado: number; valor_pago: number; funcao: string } | null;
  executores: { cnpj_executor: string; nome_executor: string; objeto: string | null }[];
  metas: { nome: string; descricao: string | null; valor_custeio: number | null; valor_investimento: number | null }[];
  pagamentos: { data_pagamento: string; valor: number | null; numero_ordem_bancaria: string | null }[];
  relatorios_gestao: { tipo: string | null; situacao: string | null; valor_executado: number | null }[];
  evidencias: EvidenciaFicha[];
  linha_do_tempo: Evento[];
  fontes: Record<string, string | null>;
}

export interface Municipio {
  codigo_ibge: string;
  nome: string;
  uf: string;
  populacao: number | null;
  ano_populacao: number | null;
  coberto_querido_diario: boolean;
  pequeno: boolean;
  status: Partial<Record<Status, number>>;
  emendas: EmendaResumo[];
  valor_repassado: number;
}

export interface Parlamentar {
  nome: string;
  perfil: PerfilParlamentar | null;
  outros_nomes_encontrados: string[];
  status: Partial<Record<Status, number>>;
  total_emendas: number;
  valor_repassado: number;
  ufs: string[];
  emendas: EmendaResumo[];
}

export interface PontoMapa {
  codigo_ibge: string;
  municipio: string;
  uf: string;
  populacao: number | null;
  emendas: number;
  repassado: number;
  status: Status;
  verde: number;
  amarelo: number;
  laranja: number;
  vermelho: number;
  azul: number;
  cinza: number;
}

export interface CoberturaUF {
  uf: string;
  entes: number;
  municipios_pequenos: number;
  pequenos_cobertos_querido_diario: number;
  entes_com_registro_pncp: number;
  entes_cobertos_tce: number;
  entes_verificados_pncp: number;
  emendas: number;
  verde: number;
  amarelo: number;
  laranja: number;
  vermelho: number;
  azul: number;
  cinza: number;
}

export interface Contagem {
  verde: number;
  amarelo: number;
  laranja: number;
  vermelho: number;
  azul: number;
  cinza: number;
}

export interface Resumo {
  emendas: number;
  valor_previsto: number;
  valor_repassado: number;
  entes: number;
  parlamentares: number;
  status: Partial<Record<Status, number>>;
  percentual_com_evidencia: number | null;
  ranking_indicios: { codigo_ibge: string; municipio: string; uf: string; vermelhas: number; repassado_vermelho: number }[];
  por_uf: ({
    uf: string;
    emendas: number;
    repassado: number;
    verde_valor: number | null;
    amarelo_valor: number | null;
    laranja_valor: number | null;
    vermelho_valor: number | null;
    azul_valor: number | null;
    cinza_valor: number | null;
  } & Contagem)[];
}

export interface AlertaResumo {
  codigo: string;
  descricao: string;
  emendas: number;
  repassado: number;
}

export interface MunicipioLista extends Contagem {
  codigo_ibge: string;
  nome: string;
  uf: string;
  populacao: number | null;
  emendas: number;
  repassado: number;
  status: Status;
}

export interface ParlamentarLista extends Contagem {
  nome: string;
  emendas: number;
  repassado: number;
  ufs: string[];
  uf_parlamentar: string | null;
  partido: string | null;
  casa: "camara" | "senado" | null;
  url_foto: string | null;
  status: Status;
}

export interface PerfilParlamentar {
  id: string;
  casa: "camara" | "senado";
  nome: string;
  nome_civil: string | null;
  partido: string | null;
  uf: string | null;
  url_foto: string | null;
  email: string | null;
  telefone: string | null;
  url_pagina: string | null;
  situacao: string | null;
  metodo_ligacao: string | null;
}

export interface Pagina<T> {
  total: number;
  pagina: number;
  tamanho: number;
  itens: T[];
}

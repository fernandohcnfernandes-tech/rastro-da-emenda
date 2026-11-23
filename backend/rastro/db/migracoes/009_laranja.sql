-- Status laranja: emenda com documento possivelmente compatível em revisão (confiança entre 45 e 59 por cento).
ALTER TYPE status_semaforo ADD VALUE IF NOT EXISTS 'laranja' AFTER 'amarelo';

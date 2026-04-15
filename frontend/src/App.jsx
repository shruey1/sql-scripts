import { useState } from 'react';

import { Header } from './components/ui/Header';
import { InputForm } from './components/InputForm';
import { ModelReview } from './components/ModelReview';
import { SQLView } from './components/SQLView';
import { ERDView } from './components/ERDView';
import { LogicalReview } from './components/LogicalReview';

import {
  generateLogicalModel,
  generateModel,
  validateAndGenerateSQL,
  approveAndGenerateSQL,
  applyFeedbackAndGenerateSQL,
  generateERD,
} from './api/client';

const BG = '#0d0f14';

export default function App() {
  const [step, setStep] = useState(0);

  // State
  const [logicalModel, setLogicalModel] = useState(null);
  const [pendingOpts, setPendingOpts] = useState(null);
  const [operation, setOperation] = useState('CREATE');
  const [validationMode, setValidationMode] = useState('auto');
  const [dataModel, setDataModel] = useState(null);
  const [validation, setValidation] = useState(null);
  const [sqlOutput, setSqlOutput] = useState(null);
  const [erdData, setErdData] = useState(null);
  const [dbEngine, setDbEngine] = useState('MySQL');
  const [loading, setLoading] = useState(false);
  const [erdLoading, setErdLoading] = useState(false);
  const [error, setError] = useState('');
  const [changes, setChanges] = useState(null);

  function wrap(fn) {
    setLoading(true);
    setError('');
    fn()
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  function reset() {
    setStep(0);
    setLogicalModel(null);
    setPendingOpts(null);
    setDataModel(null);
    setValidation(null);
    setSqlOutput(null);
    setErdData(null);
    setError('');
    setChanges(null);
  }

  // STEP 0 → STEP 1 (Generate Logical Model)
  function handleGenerate(opts) {
    wrap(async () => {
      const res = await generateLogicalModel(opts.userQuery, opts.dbEngine);
      setLogicalModel(res.logical_model);
      setPendingOpts(opts);
      setDbEngine(opts.dbEngine || 'MySQL');
      setStep(1);
    });
  }

  // STEP 1 → STEP 2 (Approve Logical Model → Physical)
  function handleLogicalApprove(modelType, approvedLogicalModel) {
    wrap(async () => {
      const res = await generateModel(
        pendingOpts.userQuery,
        'CREATE',
        null,
        modelType,
        pendingOpts.dbEngine
      );

      const engine = res.db_engine || pendingOpts.dbEngine || 'MySQL';
      const model = { ...(res.data_model || {}), db_type: engine };

      setDbEngine(engine);
      setDataModel(model);
      setOperation(res.operation || 'CREATE');
      setValidationMode(pendingOpts.validationMode || 'auto');
      setValidation(null);
      setStep(2);
    });
  }

  // STEP 2 → STEP 3 (Validation → SQL)
  function handleAutoValidate() {
    wrap(async () => {
      const model = { ...dataModel, db_type: dbEngine };
      const res = await validateAndGenerateSQL(model, operation);
      setValidation(res.validation);

      if (res.sql_output && Object.keys(res.sql_output).length > 0) {
        setSqlOutput(res.sql_output);
        setStep(3);
      }
    });
  }

  function handleApprove(applyPartitioning) {
    wrap(async () => {
      const model = { ...dataModel, db_type: dbEngine };
      const res = await approveAndGenerateSQL(model, operation, applyPartitioning);
      setSqlOutput(res.sql_output);
      setStep(3);
    });
  }

  function handleFeedback(feedbackText) {
    wrap(async () => {
      const model = { ...dataModel, db_type: dbEngine };
      const res = await applyFeedbackAndGenerateSQL(
        model,
        feedbackText,
        operation
      );

      setDataModel(res.data_model);

      if (res.sql_output && Object.keys(res.sql_output).length > 0) {
        setSqlOutput(res.sql_output);
        setStep(3);
      }
    });
  }

  // STEP 3 → STEP 4 (ERD)
  function handleSqlERD(sql) {
    setErdLoading(true);
    setError('');

    generateERD(sql)
      .then((res) => {
        setErdData(res);
        setStep(4);
      })
      .catch((e) => setError(e.message))
      .finally(() => setErdLoading(false));
  }

  return (
    <div
      style={{
        background: BG,
        minHeight: '100vh',
        color: '#e2e8f0',
        fontFamily: '"DM Sans", system-ui, sans-serif',
      }}
    >
      <style>
        {'@keyframes spin { to { transform: rotate(360deg); } }'}
      </style>

      <Header step={step} onReset={reset} />

      <div style={{ maxWidth: '100%', margin: '0 auto', padding: '24px 32px' }}>
        {/* STEP 0 */}
        {step === 0 && (
          <InputForm
            onSubmit={handleGenerate}
            loading={loading}
            error={error}
          />
        )}

        {/* STEP 1 – Logical Review */}
        {step === 1 && (
          <LogicalReview
            logicalModel={logicalModel}
            userQuery={pendingOpts?.userQuery}
            dbEngine={pendingOpts?.dbEngine}
            loading={loading}
            error={error}
            onApprove={handleLogicalApprove}
          />
        )}

        {/* STEP 2 – Physical Model */}
        {step === 2 && (
          <ModelReview
            dataModel={dataModel}
            operation={operation}
            validationMode={validationMode}
            validation={validation}
            loading={loading}
            error={error}
            onAutoValidate={handleAutoValidate}
            onApprove={handleApprove}
            onFeedback={handleFeedback}
            changes={changes}
          />
        )}

        {/* STEP 3 – SQL */}
        {step === 3 && (
          <SQLView
            sqlOutput={sqlOutput}
            validation={validation}
            onBack={() => setStep(2)}
            onReset={reset}
            onGenerateERD={handleSqlERD}
            erdLoading={erdLoading}
          />
        )}

        {/* STEP 4 – ERD */}
        {step === 4 && (
          <ERDView
            erdData={erdData}
            sqlOutput={sqlOutput}
            onBack={() => setStep(3)}
            onReset={reset}
            onRegenerate={handleSqlERD}
            loading={erdLoading}
          />
        )}
      </div>
    </div>
  );
}

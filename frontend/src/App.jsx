import { useState } from 'react';
 
import { Header } from './components/ui/Header';
import { LandingPage } from './components/LandingPage';
import { InputForm } from './components/InputForm';
import { ModelReview } from './components/ModelReview';
import { SQLView } from './components/SQLView';
import { ERDView } from './components/ERDView';
import { LogicalReview } from './components/LogicalReview';
 
import {
  generateLogicalModel,
  generateModel,
  validateModel,
  generateSQL,
  validateAndGenerateSQL,
  approveAndGenerateSQL,
  applyFeedbackAndGenerateSQL,
  generateERD,
} from './api/client';
 
const BG = '#ffffff';
 
export default function App() {
  const [step, setStep] = useState(-1);
 
  // State
  const [logicalModel, setLogicalModel] = useState(null);
  const [pendingOpts, setPendingOpts] = useState(null);
  const [lastApprovedLogicalModel, setLastApprovedLogicalModel] = useState(null);
  const [lastApprovedModelType, setLastApprovedModelType] = useState('relational');
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
    setStep(-1);
    setLogicalModel(null);
    setPendingOpts(null);
    setDataModel(null);
    setValidation(null);
    setSqlOutput(null);
    setErdData(null);
    setError('');
    setChanges(null);
  }
 
  // Landing Page → Input Form
  function handleGetStarted() {
    setStep(0);
  }
 
  // STEP 0 → STEP 1 (Generate Logical Model)
  function handleGenerate(opts) {
    wrap(async () => {
      const res = await generateLogicalModel(opts.userQuery, opts.dbEngine, opts.customKb, opts.modelType);
      setLogicalModel(res.logical_model);
      setPendingOpts(opts);
      setLastApprovedLogicalModel(null);
      setLastApprovedModelType(opts.modelType || 'relational');
      setDbEngine(opts.dbEngine || 'MySQL');
      setStep(1);
    });
  }
 
  // STEP 1 → STEP 2 (Approve Logical Model → Physical)
  function handleLogicalApprove(modelType, approvedLogicalModel) {
    wrap(async () => {
      const reuseExisting =
        dataModel &&
        lastApprovedLogicalModel &&
        lastApprovedModelType === modelType &&
        JSON.stringify(lastApprovedLogicalModel) === JSON.stringify(approvedLogicalModel);
 
      if (reuseExisting) {
        setStep(2);
        return;
      }
 
      const res = await generateModel(
        pendingOpts.userQuery,
        'CREATE',
        null,
        modelType,
        pendingOpts.dbEngine,
        pendingOpts.customKb,
        approvedLogicalModel
      );
 
      const engine = res.db_engine || pendingOpts.dbEngine || 'MySQL';
      const model = { ...(res.data_model || {}), db_type: engine };
 
      setDbEngine(engine);
      setDataModel(model);
      setLastApprovedLogicalModel(approvedLogicalModel);
      setLastApprovedModelType(modelType);
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
 
      // Only move to step 3 if validation passes
      if (res.validation && res.validation.is_valid && res.sql_output && Object.keys(res.sql_output).length > 0) {
        setSqlOutput(res.sql_output);
        setStep(3);
      }
      // If validation fails, stay at step 2 to show validation errors and allow feedback
    });
  }
 
  // STEP 2: Validate only (no SQL generation yet)
  function handleValidateOnly() {
    wrap(async () => {
      const model = { ...dataModel, db_type: dbEngine };
      const res = await validateModel(model, operation);
      setValidation(res.validation);
    });
  }
 
  // STEP 2: Generate SQL (from already-validated model)
  function handleGenerateSQL() {
    wrap(async () => {
      const model = { ...dataModel, db_type: dbEngine };
      const res = await generateSQL(model, operation);
      setSqlOutput(res.sql_output);
      setStep(3);
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
      setValidation(null); // Reset validation state
      setSqlOutput(null); // Clear any previous SQL
 
      // Auto-validate the updated model
      if (validationMode === 'auto') {
        const valRes = await validateModel(res.data_model, dbEngine);
        setValidation(valRes.validation);
       
        // ONLY move to step 3 if validation passes
        if (valRes.validation && valRes.validation.is_valid) {
          setSqlOutput(res.sql_output);
          setStep(3);
        }
        // If validation fails, stay at step 2 to show errors and allow more feedback
      } else {
        // Manual validation mode: don't auto-validate, just apply changes
        // User will click "Approve & Generate SQL" themselves
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
 
      {/* Landing Page */}
      {step === -1 && <LandingPage onGetStarted={handleGetStarted} />}
 
      {/* Main App */}
      {step >= 0 && (
        <>
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
                modelType={pendingOpts?.modelType || 'both'}
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
                onValidateOnly={handleValidateOnly}
                onGenerateSQL={handleGenerateSQL}
                onApprove={handleApprove}
                onFeedback={handleFeedback}
                onBack={() => setStep(1)}
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
        </>
      )}
    </div>
  );
}
 
 
/**
 * FormationPicker - Formation and personnel selection
 *
 * Shows visual formation diagrams with personnel options.
 */

import React from 'react';
import type { Formation, PersonnelGroup } from '../../types';
import { FORMATIONS, PERSONNEL_GROUPS } from '../../constants';

interface FormationPickerProps {
  selectedFormation: Formation | null;
  selectedPersonnel: PersonnelGroup;
  onFormationChange: (formation: Formation) => void;
  onPersonnelChange: (personnel: PersonnelGroup) => void;
}

// Simplified formation dots for buttons
const FORMATION_DOTS: Record<Formation, { skill: number; backfield: number[] }> = {
  shotgun: { skill: 3, backfield: [1, 1] }, // QB offset, RB next to
  i_form: { skill: 2, backfield: [1, 1, 1] }, // QB, FB, RB stacked
  singleback: { skill: 3, backfield: [1, 1] },
  pistol: { skill: 3, backfield: [1, 1] }, // QB, RB stacked
  empty: { skill: 5, backfield: [1] }, // Just QB
  goal_line: { skill: 1, backfield: [1, 2] }, // QB, FB+RB side by side
  jumbo: { skill: 1, backfield: [1, 2] },
};

export const FormationPicker: React.FC<FormationPickerProps> = ({
  selectedFormation,
  selectedPersonnel,
  onFormationChange,
  onPersonnelChange,
}) => {
  // Get valid personnel for selected formation
  const validPersonnel = selectedFormation
    ? FORMATIONS[selectedFormation].personnel
    : ['11', '12', '21'];

  return (
    <div className="formation-picker">
      <h4 className="formation-picker__title">FORMATION</h4>

      {/* Formation grid */}
      <div className="formation-picker__grid">
        {(['shotgun', 'i_form', 'singleback', 'pistol'] as Formation[]).map(formation => (
          <button
            key={formation}
            className={`formation-picker__btn ${selectedFormation === formation ? 'active' : ''}`}
            onClick={() => onFormationChange(formation)}
            title={FORMATIONS[formation].description}
          >
            <div className="formation-picker__dots">
              <FormationMiniDots formation={formation} />
            </div>
            <span className="formation-picker__name">
              {FORMATIONS[formation].name}
            </span>
          </button>
        ))}
      </div>

      {/* Personnel selector */}
      <div className="formation-picker__personnel">
        <span className="formation-picker__personnel-label">Personnel:</span>
        <div className="formation-picker__personnel-btns">
          {(['11', '12', '21', '22'] as PersonnelGroup[]).map(pers => (
            <button
              key={pers}
              className={`formation-picker__personnel-btn ${selectedPersonnel === pers ? 'active' : ''} ${!validPersonnel.includes(pers) ? 'disabled' : ''}`}
              onClick={() => validPersonnel.includes(pers) && onPersonnelChange(pers)}
              title={PERSONNEL_GROUPS[pers].description}
              disabled={!validPersonnel.includes(pers)}
            >
              {pers}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

// Mini formation dots for button preview
const FormationMiniDots: React.FC<{ formation: Formation }> = ({ formation }) => {
  const config = FORMATION_DOTS[formation];

  return (
    <div className="formation-mini-dots">
      {/* Skill players row */}
      <div className="formation-mini-dots__row">
        {Array.from({ length: config.skill }).map((_, i) => (
          <span key={`skill-${i}`} className="formation-mini-dots__dot formation-mini-dots__dot--skill" />
        ))}
      </div>
      {/* O-line row */}
      <div className="formation-mini-dots__row formation-mini-dots__row--line">
        {Array.from({ length: 5 }).map((_, i) => (
          <span
            key={`ol-${i}`}
            className={`formation-mini-dots__dot formation-mini-dots__dot--line ${i === 2 ? 'formation-mini-dots__dot--center' : ''}`}
          />
        ))}
      </div>
      {/* Backfield row(s) */}
      {config.backfield.map((count, rowIndex) => (
        <div key={`bf-${rowIndex}`} className="formation-mini-dots__row formation-mini-dots__row--backfield">
          {Array.from({ length: count }).map((_, i) => (
            <span
              key={`bf-${rowIndex}-${i}`}
              className={`formation-mini-dots__dot ${rowIndex === 0 && i === 0 ? 'formation-mini-dots__dot--qb' : 'formation-mini-dots__dot--rb'}`}
            />
          ))}
        </div>
      ))}
    </div>
  );
};

export default FormationPicker;

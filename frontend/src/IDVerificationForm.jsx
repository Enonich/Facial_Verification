import React, { useState } from 'react';

function IDVerificationForm({ onFormSubmit, onCancel }) {
  const [formData, setFormData] = useState({
    surname: '',
    firstName: '',
    otherNames: '',
    idType: 'GH_CARD',
    idNumber: ''
  });

  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const idTypeOptions = [
    { value: 'GH_CARD', label: 'Ghana Card', placeholder: 'e.g., GHA-123456789-0' },
    { value: 'VOTERS_ID', label: "Voter's ID Card", placeholder: 'e.g., 123456789' },
    { value: 'PASSPORT', label: 'Passport', placeholder: 'e.g., A12345678' }
  ];

  const validateForm = () => {
    const newErrors = {};

    if (!formData.surname.trim()) {
      newErrors.surname = 'Surname is required';
    } else if (formData.surname.trim().length < 2) {
      newErrors.surname = 'Surname must be at least 2 characters';
    } else if (!/^[a-zA-Z\s'-]+$/.test(formData.surname)) {
      newErrors.surname = 'Surname should contain only letters, spaces, and hyphens';
    }

    if (!formData.firstName.trim()) {
      newErrors.firstName = 'First name is required';
    } else if (formData.firstName.trim().length < 2) {
      newErrors.firstName = 'First name must be at least 2 characters';
    } else if (!/^[a-zA-Z\s'-]+$/.test(formData.firstName)) {
      newErrors.firstName = 'First name should contain only letters, spaces, and hyphens';
    }

    if (formData.otherNames && !/^[a-zA-Z\s'-]*$/.test(formData.otherNames)) {
      newErrors.otherNames = 'Other names should contain only letters, spaces, and hyphens';
    }

    if (!formData.idNumber.trim()) {
      newErrors.idNumber = 'ID number is required';
    } else if (formData.idType === 'GH_CARD') {
      // Ghana Card format: GHA-XXXXXXXXX-X
      if (!/^GHA-\d{9}-\d$/.test(formData.idNumber)) {
        newErrors.idNumber = 'Invalid Ghana Card format (e.g., GHA-123456789-0)';
      }
    } else if (formData.idType === 'VOTERS_ID') {
      // Voter's ID: 8-12 digits
      if (!/^\d{8,12}$/.test(formData.idNumber)) {
        newErrors.idNumber = 'Invalid Voter ID format (8-12 digits)';
      }
    } else if (formData.idType === 'PASSPORT') {
      // Passport: Usually alphanumeric, flexible
      if (!/^[A-Z0-9]{6,12}$/.test(formData.idNumber)) {
        newErrors.idNumber = 'Invalid Passport format (6-12 alphanumeric characters)';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error for this field when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    
    try {
      // Call parent handler with form data
      await onFormSubmit(formData);
    } catch (error) {
      console.error('Form submission error:', error);
      setErrors({ submit: 'An error occurred. Please try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const currentIdType = idTypeOptions.find(opt => opt.value === formData.idType);

  return (
    <div className="id-verification-form">
      <div className="form-header">
        <h3>📋 Enter Your Details</h3>
        <p>Please provide your personal information and ID details to begin verification</p>
      </div>

      <form onSubmit={handleSubmit} className="form-content">
        {/* Surname Field */}
        <div className="form-group">
          <label htmlFor="surname" className="form-label">
            Surname <span className="required">*</span>
          </label>
          <input
            type="text"
            id="surname"
            name="surname"
            value={formData.surname}
            onChange={handleInputChange}
            placeholder="Enter your surname"
            className={`form-input ${errors.surname ? 'error' : ''}`}
            disabled={isSubmitting}
            autoComplete="family-name"
          />
          {errors.surname && (
            <span className="field-error">⚠️ {errors.surname}</span>
          )}
        </div>

        {/* First Name Field */}
        <div className="form-group">
          <label htmlFor="firstName" className="form-label">
            First Name <span className="required">*</span>
          </label>
          <input
            type="text"
            id="firstName"
            name="firstName"
            value={formData.firstName}
            onChange={handleInputChange}
            placeholder="Enter your first name"
            className={`form-input ${errors.firstName ? 'error' : ''}`}
            disabled={isSubmitting}
            autoComplete="given-name"
          />
          {errors.firstName && (
            <span className="field-error">⚠️ {errors.firstName}</span>
          )}
        </div>

        {/* Other Names Field */}
        <div className="form-group">
          <label htmlFor="otherNames" className="form-label">
            Other Names / Middle Names
          </label>
          <input
            type="text"
            id="otherNames"
            name="otherNames"
            value={formData.otherNames}
            onChange={handleInputChange}
            placeholder="Enter any other names (optional)"
            className={`form-input ${errors.otherNames ? 'error' : ''}`}
            disabled={isSubmitting}
            autoComplete="additional-name"
          />
          {errors.otherNames && (
            <span className="field-error">⚠️ {errors.otherNames}</span>
          )}
          <p className="field-hint">Leave blank if you don't have other names</p>
        </div>

        {/* ID Type Selection */}
        <div className="form-group">
          <label htmlFor="idType" className="form-label">
            ID Type <span className="required">*</span>
          </label>
          <select
            id="idType"
            name="idType"
            value={formData.idType}
            onChange={handleInputChange}
            className="form-select"
            disabled={isSubmitting}
          >
            {idTypeOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <p className="field-hint">Select the type of ID you will upload</p>
        </div>

        {/* ID Number Field */}
        <div className="form-group">
          <label htmlFor="idNumber" className="form-label">
            {formData.idType === 'GH_CARD' && 'Ghana Card Number'}
            {formData.idType === 'VOTERS_ID' && 'Voter ID Number'}
            {formData.idType === 'PASSPORT' && 'Passport Number'}
            <span className="required">*</span>
          </label>
          <input
            type="text"
            id="idNumber"
            name="idNumber"
            value={formData.idNumber}
            onChange={handleInputChange}
            placeholder={currentIdType?.placeholder || 'Enter ID number'}
            className={`form-input ${errors.idNumber ? 'error' : ''}`}
            disabled={isSubmitting}
            autoComplete="off"
          />
          {errors.idNumber && (
            <span className="field-error">⚠️ {errors.idNumber}</span>
          )}
          <p className="field-hint">
            {formData.idType === 'GH_CARD' && 'Format: GHA-123456789-0'}
            {formData.idType === 'VOTERS_ID' && 'Enter your 8-12 digit voter ID'}
            {formData.idType === 'PASSPORT' && 'Enter your passport number'}
          </p>
        </div>

        {/* Submission Error */}
        {errors.submit && (
          <div className="form-error-message">
            ❌ {errors.submit}
          </div>
        )}

        {/* Form Actions */}
        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary btn-large"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <span className="spinner-small"></span>
                Processing...
              </>
            ) : (
              <>
                <span>✓</span>
                Continue to ID Upload
              </>
            )}
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-large"
            onClick={onCancel}
            disabled={isSubmitting}
          >
            Cancel
          </button>
        </div>

        <p className="form-note">
          💡 Your information will be verified against the ID document you upload.
        </p>
      </form>
    </div>
  );
}

export default IDVerificationForm;

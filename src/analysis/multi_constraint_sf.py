import numpy as np
import pandas as pd
from scipy.linalg import lstsq


def calculate_shift_factors_multiple_constraints(mcc_df, shadow_prices_df, tolerance=1e-6):
   """
   Calculate shift factors when multiple constraints are binding simultaneously
  
   Parameters:
   - mcc_df: DataFrame with columns ['Interval', 'Settlement_Location', 'MCC']
   - shadow_prices_df: DataFrame with columns ['Interval', 'Constraint_Name', 'Shadow_Price']
   - tolerance: threshold for considering a shadow price non-zero
  
   Returns: Dictionary of shift factors by interval
   """
   results = {}
  
   # Group by interval to handle each timestamp separately
   for interval, interval_shadow_prices in shadow_prices_df.groupby('Interval'):
       # Get binding constraints (non-zero shadow prices)
       binding = interval_shadow_prices[abs(interval_shadow_prices['Shadow_Price']) > tolerance]
      
       if len(binding) > 0:  # If we have binding constraints
           # Get MCCs for this interval
           interval_mccs = mcc_df[mcc_df['Interval'] == interval]
          
           if len(binding) == 1:
               # Simple case - single binding constraint
               constraint = binding.iloc[0]
               shift_factors = {
                   node: mcc / constraint['Shadow_Price']
                   for node, mcc in zip(interval_mccs['Settlement_Location'],
                                      interval_mccs['MCC'])
               }
              
           else:
               # Multiple binding constraints - use matrix solution
               # Build shadow price matrix (A)
               A = np.diag(binding['Shadow_Price'].values)  # Create diagonal matrix of shadow prices
              
               # Build MCC vector (B) for each node
               shift_factors = {}
               for node in interval_mccs['Settlement_Location'].unique():
                   # Get the MCC value for this node
                   node_mcc = interval_mccs[
                       interval_mccs['Settlement_Location'] == node
                   ]['MCC'].values[0]
                   
                   # Create a vector of the same length as binding constraints
                   node_mcc_vector = np.full(len(binding), node_mcc).reshape(-1, 1)
                   
                   # Solve for shift factors using least squares
                   sf, residuals, rank, s = lstsq(A, node_mcc_vector)
                  
                   # Store results if solution is valid
                   if validate_shift_factors(sf, A, node_mcc_vector):
                       shift_factors[node] = {
                           constraint: sf[i][0]
                           for i, constraint in enumerate(binding['Constraint_Name'])
                       }
          
           results[interval] = {
               'shift_factors': shift_factors,
               'binding_constraints': binding['Constraint_Name'].tolist()
           }
  
   return results


def validate_shift_factors(shift_factors, shadow_prices, mccs, tolerance=1e-6):
   """
   Validate calculated shift factors
   """
   # Check physical bounds
   if not np.all((-1 <= shift_factors) & (shift_factors <= 1)):
       return False
  
   # Check reconstruction error
   reconstructed_mccs = np.dot(shadow_prices, shift_factors)
   if np.any(abs(reconstructed_mccs - mccs) > tolerance):
       return False
  
   return True


def analyze_results(results):
   """
   Analyze and summarize shift factor results
   """
   summary = {}
  
   for interval, data in results.items():
       shift_factors = data['shift_factors']
       constraints = data['binding_constraints']
      
       # Calculate statistics for each constraint
       for constraint in constraints:
           constraint_sfs = [
               sfs[constraint]
               for sfs in shift_factors.values()
               if constraint in sfs
           ]
          
           summary[f"{interval}_{constraint}"] = {
               'mean_sf': np.mean(constraint_sfs),
               'max_sf': np.max(constraint_sfs),
               'min_sf': np.min(constraint_sfs),
               'std_sf': np.std(constraint_sfs)
           }
  
   return pd.DataFrame(summary).T


def parse_rtbm_data(lmp_file_path, binding_constraints_file_path):
    """
    Parse RTBM LMP and Binding Constraints data files
    
    Parameters:
    - lmp_file_path: Path to the RTBM LMP CSV file
    - binding_constraints_file_path: Path to the RTBM Binding Constraints CSV file
    
    Returns:
    - mcc_data: Dictionary with MCC data
    - shadow_prices_data: Dictionary with shadow prices data
    """
    # Read LMP data
    lmp_df = pd.read_csv(lmp_file_path)
    
    # Extract interval and settlement location data
    interval = lmp_df.iloc[0]['Interval']  # Get first interval
    
    # MCC is the third-to-last column (LMP components are in fixed positions)
    mcc_data = {
        'Interval': [],
        'Settlement_Location': [],
        'MCC': []
    }
    
    for _, row in lmp_df.iterrows():
        # Split row into columns and extract values
        cols = list(row)
        if len(cols) >= 4:  # Ensure we have enough columns
            mcc_data['Interval'].append(interval)
            mcc_data['Settlement_Location'].append(cols[2])  # Settlement Location is 3rd column
            mcc_data['MCC'].append(float(cols[-2]))  # MCC is second-to-last column
    
    # Read binding constraints data
    bc_df = pd.read_csv(binding_constraints_file_path)
    
    # Extract shadow prices for binding constraints
    shadow_prices_data = {
        'Interval': [],
        'Constraint_Name': [],
        'Shadow_Price': []
    }
    
    for _, row in bc_df.iterrows():
        if row['State'] == 'BINDING':  # Only include binding constraints
            shadow_prices_data['Interval'].append(interval)
            shadow_prices_data['Constraint_Name'].append(row['Constraint Name'])
            shadow_prices_data['Shadow_Price'].append(float(row['Shadow Price']))
    
    return mcc_data, shadow_prices_data


def main():
    # Parse data from CSV files
    mcc_data, shadow_prices_data = parse_rtbm_data(
        'src/data/RTBM-LMP-SL-202501230225.csv',
        'src/data/RTBM-BC-202501230225.csv'
    )
    
    # Convert to DataFrames
    mcc_df = pd.DataFrame(mcc_data)
    shadow_prices_df = pd.DataFrame(shadow_prices_data)
    
    # Calculate shift factors
    results = calculate_shift_factors_multiple_constraints(mcc_df, shadow_prices_df)
    
    # Create a list to store all shift factor data
    shift_factor_data = []
    
    # Collect data for CSV
    for interval, data in results.items():
        for node, sfs in data['shift_factors'].items():
            for constraint, sf in sfs.items():
                shift_factor_data.append({
                    'Interval': interval,
                    'Node': node,
                    'Constraint': constraint,
                    'Shift_Factor': sf
                })
    
    # Convert to DataFrame and save as CSV
    if shift_factor_data:
        sf_df = pd.DataFrame(shift_factor_data)
        csv_filename = 'shift_factors_output.csv'
        sf_df.to_csv(csv_filename, index=False)
        print(f"\nShift factors saved to {csv_filename}")
        
        # Analyze results
        summary = analyze_results(results)
        
        # Also print summary statistics
        print("\nShift Factor Summary:")
        print(summary)
    else:
        print("\nNo results found.")


if __name__ == "__main__":
   main()
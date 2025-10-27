from django import forms
from .models import Worker, WorkerAttendance, OutsourcedGroup

class WorkerForm(forms.ModelForm):
    # New fields to handle group creation and leader assignment dynamically
    new_group_name = forms.CharField(
        required=False,
        label="Or Create New Group Name",
        help_text="Fill this in if the group doesn't exist in the dropdown."
    )
    is_leader = forms.BooleanField(
        required=False,
        label="Set this worker as the leader of their group"
    )

    class Meta:
        model = Worker
        # Updated fields to include 'dob'
        fields = [
            'name', 'worker_type', 'dob', 'group', 'contact', 
            'fixed_wage', 'daily_wage', 'ot1_rate', 'ot2_rate', 'is_active'
        ]
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The 'group' dropdown is optional because the user can create a new group instead
        self.fields['group'].required = False

    def clean(self):
        cleaned_data = super().clean()
        worker_type = cleaned_data.get('worker_type')
        dob = cleaned_data.get('dob')

        # --- New DOB Validation ---
        if worker_type == 'own' and not dob:
            self.add_error('dob', "Date of Birth is required for 'Own' workers.")
        
        # --- Existing Group/Wage Validation ---
        group = cleaned_data.get('group')
        new_group_name = cleaned_data.get('new_group_name')

        if worker_type == 'outsourced':
            if not group and not new_group_name:
                raise forms.ValidationError(
                    "An outsourced worker must belong to a group. Please select an existing group or create a new one.",
                    code='no_group'
                )
            if group and new_group_name:
                raise forms.ValidationError(
                    "Please either select an existing group or create a new one, not both.",
                    code='both_groups'
                )
            if new_group_name and OutsourcedGroup.objects.filter(name__iexact=new_group_name).exists():
                self.add_error('new_group_name', 'A group with this name already exists.')

        fixed_wage = cleaned_data.get('fixed_wage')
        daily_wage = cleaned_data.get('daily_wage')
        if worker_type == 'own' and (fixed_wage is None or fixed_wage <= 0):
            self.add_error('fixed_wage', "A monthly salary is required for an 'Own' Worker.")
        if worker_type == 'outsourced' and (daily_wage is None or daily_wage <= 0):
            self.add_error('daily_wage', "A daily wage is required for an 'Outsourced' Worker.")

        return cleaned_data

    def save(self, commit=True):
        # Temporarily save the worker instance to get an object to work with
        worker = super().save(commit=False)
        
        new_group_name = self.cleaned_data.get('new_group_name')
        is_leader = self.cleaned_data.get('is_leader')
        group = self.cleaned_data.get('group')

        created_group = None
        if new_group_name:
            # Create the new group if a name was provided
            created_group = OutsourcedGroup.objects.create(name=new_group_name)
            worker.group = created_group
        
        if commit:
            worker.save()

        # Now that the worker has an ID, we can assign them as a leader
        target_group = created_group or group
        if target_group and is_leader:
            target_group.leader = worker
            target_group.save()
        
        return worker

class WorkerAttendanceForm(forms.ModelForm):
    # Use specific time widgets for better UX
    in_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    out_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))

    class Meta:
        model = WorkerAttendance
        fields = ['worker', 'project', 'date', 'in_time', 'out_time', 'is_holiday', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def clean(self):
        # Ensure that the out-time is always after the in-time
        cleaned_data = super().clean()
        in_time = cleaned_data.get("in_time")
        out_time = cleaned_data.get("out_time")
        if in_time and out_time and out_time <= in_time:
            raise forms.ValidationError("Out time must be after in time.")
        return cleaned_data


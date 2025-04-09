class BudgetCreateView(SuperuserRequiredMixin, CreateView):
    model = Budget
    form_class = BudgetForm
    template_name = 'core/budget_create.html'

    def form_valid(self, form):
        budget = form.save(commit=False)
        budget.elaborador = self.request.user

        try:
            with transaction.atomic():
                budget.save()
                version = BudgetVersion.objects.create(budget=budget, total=0)
                self.request.session['current_version'] = version.id
        except IntegrityError:
            # Tratar erro de código legado duplicado
            return self.form_invalid(form)

        return redirect('budget_edit', pk=budget.pk)


class BudgetEditView(SuperuserRequiredMixin, UpdateView):
    model = Budget
    form_class = BudgetForm
    template_name = 'core/budget_edit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        version = get_object_or_404(BudgetVersion, pk=self.request.session.get('current_version'))
        context['item_formset'] = BudgetItemFormSet(instance=version)
        return context
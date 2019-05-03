from rest_framework.generics import ListAPIView


class BaseSearchTemplate(ListAPIView):
    def get_queryset(self):
        queryset = self.template_model.objects.filter(flag='public')
        name = self.request.GET.get('name', None)
        des = self.request.GET.get('des', None)
        if name:
            print(name, "\n\n\n")
            queryset = queryset.filter(name__contains='{}'.format(name))
            for i in queryset:
                print(i.name)
            print("\n\n\n\n")
        if des:
            queryset = queryset.filter(description__contains=des)
        return queryset

'''Module to generate classes.'''


class ClassFactory:
    '''
    This class servers as baseclass a classfactory.

    See ClassFactory.customize for more details.
    '''

    @classmethod
    def customize(cls, **kwargs):
        '''
        Create a new class from the given baseclass with additional class attributes.

        The new class will aditionally contain the classattributes specified by kwargs.

        Example:

        class MyClass(ClassFactory, ...):
        #   ...

        MyClass.customize(foo=42, bar='foobar')
        # Returns a class with the additional classattributes foo and bar set to 42 and 'foobar'.
        '''

        class C(cls):
            '''Classfactory generated class.'''

            pass
        for key, value in kwargs.items():
            setattr(C, key, value)
        return C
